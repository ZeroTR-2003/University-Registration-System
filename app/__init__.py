"""Flask application factory and initialization."""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, render_template, redirect
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_mail import Mail
from flasgger import Swagger
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from celery import Celery
from flask_wtf.csrf import CSRFProtect

from config import config
from app.models import db

# Initialize extensions
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()
mail = Mail()
swagger = Swagger()
cache = Cache()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
csrf = CSRFProtect()
celery = None


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Check Redis availability early and fall back to in-memory stores if needed.
    redis_available = False
    try:
        import redis as _redis
        # Try a quick ping using the configured URL; timeouts kept small for startup speed
        try:
            client = _redis.from_url(app.config.get('REDIS_URL'), socket_connect_timeout=1, socket_timeout=1)
            client.ping()
            redis_available = True
        except Exception:
            redis_available = False
            app.logger and app.logger.warning('Redis not available at %s - falling back to in-memory caches', app.config.get('REDIS_URL'))
    except Exception:
        # redis library not present or other import error
        redis_available = False
        app.logger and app.logger.warning('redis library not available - falling back to in-memory caches')
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    mail.init_app(app)
    swagger.init_app(app)
    # Global CSRF protection (exempt API routes below)
    csrf.init_app(app)

    # Caching (attempt Redis in prod; fall back to SimpleCache when Redis not reachable)
    if config_name == 'production' and redis_available:
        cache.init_app(app, config={'CACHE_TYPE': 'RedisCache', 'CACHE_REDIS_URL': app.config['REDIS_URL']})
    elif app.testing:
        cache.init_app(app, config={'CACHE_TYPE': 'NullCache'})
    else:
        cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache'})

    # Rate limiting
    # Ensure limiter uses a safe storage backend when Redis is not available.
    if not redis_available and app.config.get('RATELIMIT_STORAGE_URI', '').startswith('redis'):
        app.config['RATELIMIT_STORAGE_URI'] = 'memory://'
    limiter.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.api import api_bp
    from app.auth import auth_bp
    from app.main import main_bp
    from app.student import student_bp
    from app.instructor import instructor_bp
    from app.admin import admin_bp
    from app.registrar import registrar_bp

    # Exempt API blueprint from CSRF to avoid breaking JSON clients
    csrf.exempt(api_bp)
    
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(instructor_bp, url_prefix='/instructor')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(registrar_bp, url_prefix='/registrar')
    
    # Error handlers
    register_error_handlers(app)

    # API docs shortcut
    @app.route('/api/docs')
    def api_docs_redirect():
        return redirect('/apidocs')
    
    # Logging setup
    if not app.debug and not app.testing:
        setup_logging(app)
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Celery
    global celery
    celery = make_celery(app)
    
    # Template context processor to make current_app available
    @app.context_processor
    def inject_current_app():
        from flask import current_app
        return {'current_app': current_app}

    @app.context_processor
    def inject_unread_notifications():
        # Provide unread notification count in all templates
        count = 0
        try:
            from flask_login import current_user as _cu
            from app.models import Notification as _Note
            if _cu.is_authenticated:
                count = _Note.query.filter_by(user_id=_cu.id, is_read=False).count()
        except Exception:
            count = 0
        return {'unread_notifications': count}
    
    # Shell context for debugging
    @app.shell_context_processor
    def make_shell_context():
        from app.models import (
            User, Role, StudentProfile, InstructorProfile,
            Department, Course, CourseSection, Enrollment,
            Assignment, Submission, Room, Building,
            Announcement, Notification, AuditLog, Media, TranscriptRequest
        )
        return {
            'db': db,
            'User': User,
            'Role': Role,
            'StudentProfile': StudentProfile,
            'InstructorProfile': InstructorProfile,
            'Department': Department,
            'Course': Course,
            'CourseSection': CourseSection,
            'Enrollment': Enrollment,
            'Assignment': Assignment,
            'Submission': Submission,
            'Room': Room,
            'Building': Building,
            'Announcement': Announcement,
            'Notification': Notification,
            'AuditLog': AuditLog,
            'Media': Media,
            'TranscriptRequest': TranscriptRequest
        }
    
    # Create database tables
    with app.app_context():
        if app.config.get('CREATE_TABLES_ON_START', False):
            db.create_all()
            # Insert default roles
            from app.models.user import Role
            Role.insert_default_roles()
    
    return app


def register_error_handlers(app):
    """Register error handlers."""
    
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500


def setup_logging(app):
    """Set up logging for production."""
    if app.config['LOG_TO_STDOUT']:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)
    else:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/university.log',
                                          maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
    
    app.logger.setLevel(logging.INFO)
    app.logger.info('University Registration System startup')


# Import and register user loader for Flask-Login and request/json helpers
from flask_login import current_user
from flask import request, jsonify


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    from app.models.user import User
    return User.query.get(int(user_id))


@jwt.user_identity_loader
def user_identity_lookup(user):
    """Get user identity for JWT."""
    return user.id


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """Load user from JWT."""
    from app.models.user import User
    identity = jwt_data["sub"]
    return User.query.filter_by(id=identity).one_or_none()


def make_celery(app):
    """Create Celery application bound to Flask app context."""
    celery_app = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery_app.conf.update(result_backend=app.config['CELERY_RESULT_BACKEND'])

    class AppContextTask(celery_app.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)

    celery_app.Task = AppContextTask
    return celery_app
