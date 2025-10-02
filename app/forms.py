"""Forms for the University Registration System."""

from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, SubmitField,
                     SelectField, TextAreaField, FloatField, IntegerField,
                     DateField, TimeField, FileField, SelectMultipleField)
from wtforms.validators import (DataRequired, Email, EqualTo, Length,
                                Optional, NumberRange, ValidationError)
from app.models import User, Course, CourseSection


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    """User registration form (admin creates new user)."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    role = SelectField('Role', choices=[
        ('student', 'Student'),
        ('instructor', 'Instructor')
    ], validators=[DataRequired()])
    
    # Contact information
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    birth_date = DateField('Date of Birth', validators=[Optional()], format='%Y-%m-%d')
    
    # Address fields
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State/Province', validators=[Optional(), Length(max=50)])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=20)])
    country = StringField('Country', validators=[Optional(), Length(max=100)])
    
    # Optional department for instructor accounts
    department_id = SelectField('Department (for Instructor)', coerce=int, validators=[Optional()])
    submit = SubmitField('Register')

    def validate_email(self, email):
        """Check if email already exists."""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email address already registered.')


class ProfileForm(FlaskForm):
    """User profile update form."""
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    phone_number = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    address_line1 = StringField('Address Line 1', validators=[Optional(), Length(max=200)])
    address_line2 = StringField('Address Line 2', validators=[Optional(), Length(max=200)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State', validators=[Optional(), Length(max=50)])
    postal_code = StringField('Postal Code', validators=[Optional(), Length(max=20)])
    country = StringField('Country', validators=[Optional(), Length(max=100)])
    birth_date = DateField('Birth Date', validators=[Optional()])
    submit = SubmitField('Update Profile')


class StudentProfileForm(FlaskForm):
    """Student-specific profile form."""
    student_number = StringField('Student Number', validators=[DataRequired(), Length(max=20)])
    program = StringField('Program', validators=[Optional(), Length(max=100)])
    degree_type = SelectField('Degree Type', choices=[
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('phd', 'PhD'),
        ('certificate', 'Certificate')
    ], validators=[Optional()])
    major = StringField('Major', validators=[Optional(), Length(max=100)])
    minor = StringField('Minor', validators=[Optional(), Length(max=100)])
    enrollment_year = IntegerField('Enrollment Year', validators=[DataRequired()])
    graduation_year = IntegerField('Expected Graduation Year', validators=[Optional()])
    emergency_contact_name = StringField('Emergency Contact Name', validators=[Optional()])
    emergency_contact_phone = StringField('Emergency Contact Phone', validators=[Optional()])
    submit = SubmitField('Update Student Profile')


class InstructorProfileForm(FlaskForm):
    """Instructor-specific profile form."""
    employee_number = StringField('Employee Number', validators=[DataRequired(), Length(max=20)])
    title = SelectField('Title', choices=[
        ('professor', 'Professor'),
        ('associate_professor', 'Associate Professor'),
        ('assistant_professor', 'Assistant Professor'),
        ('lecturer', 'Lecturer'),
        ('adjunct', 'Adjunct Professor')
    ], validators=[Optional()])
    office_building = StringField('Office Building', validators=[Optional(), Length(max=100)])
    office_room = StringField('Office Room', validators=[Optional(), Length(max=20)])
    office_phone = StringField('Office Phone', validators=[Optional(), Length(max=20)])
    bio = TextAreaField('Professional Biography', validators=[Optional()])
    research_interests = TextAreaField('Research Interests', validators=[Optional()])
    submit = SubmitField('Update Instructor Profile')


class CourseForm(FlaskForm):
    """Course creation/edit form."""
    code = StringField('Course Code', validators=[DataRequired(), Length(max=20)])
    title = StringField('Course Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    credits = FloatField('Credits', validators=[DataRequired(), NumberRange(min=0, max=12)])
    level = SelectField('Level', choices=[
        ('undergraduate', 'Undergraduate'),
        ('graduate', 'Graduate'),
        ('doctoral', 'Doctoral')
    ], validators=[DataRequired()])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    prerequisites = SelectMultipleField('Prerequisites', coerce=int, validators=[Optional()])
    max_capacity_default = IntegerField('Default Capacity', validators=[Optional(), NumberRange(min=1)])
    lab_required = BooleanField('Lab Required')
    submit = SubmitField('Save Course')


class CourseSectionForm(FlaskForm):
    """Course section creation/edit form."""
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    section_code = StringField('Section Code', validators=[DataRequired(), Length(max=10)])
    term = StringField('Term', validators=[DataRequired(), Length(max=20)])
    instructor_id = SelectField('Instructor', coerce=int, validators=[Optional()])
    capacity = IntegerField('Capacity', validators=[DataRequired(), NumberRange(min=1)])
    room_id = SelectField('Room', coerce=int, validators=[Optional()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    delivery_mode = SelectField('Delivery Mode', choices=[
        ('In-Person', 'In-Person'),
        ('Online', 'Online'),
        ('Hybrid', 'Hybrid')
    ], validators=[DataRequired()])
    allow_audit = BooleanField('Allow Audit')
    require_permission = BooleanField('Require Permission')
    submit = SubmitField('Save Section')


class EnrollmentForm(FlaskForm):
    """Course enrollment form."""
    course_section_id = SelectField('Course Section', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    audit = BooleanField('Audit Only')
    submit = SubmitField('Enroll')


class AssignmentForm(FlaskForm):
    """Assignment creation/edit form."""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    type = SelectField('Type', choices=[
        ('homework', 'Homework'),
        ('quiz', 'Quiz'),
        ('exam', 'Exam'),
        ('project', 'Project'),
        ('lab', 'Lab'),
        ('presentation', 'Presentation'),
        ('paper', 'Paper')
    ], validators=[DataRequired()])
    points = FloatField('Points', validators=[DataRequired(), NumberRange(min=0)])
    due_date = DateField('Due Date', validators=[DataRequired()])
    due_time = TimeField('Due Time', validators=[Optional()])
    allow_late = BooleanField('Allow Late Submission')
    late_penalty_per_day = FloatField('Late Penalty % Per Day', validators=[Optional(), NumberRange(min=0, max=100)])
    submit = SubmitField('Save Assignment')


class SubmissionForm(FlaskForm):
    """Assignment submission form."""
    content = TextAreaField('Submission Content', validators=[Optional()])
    file = FileField('Upload File', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Submit Assignment')


class GradeForm(FlaskForm):
    """Grade assignment form."""
    score = FloatField('Score', validators=[DataRequired(), NumberRange(min=0)])
    feedback = TextAreaField('Feedback', validators=[Optional()])
    submit = SubmitField('Save Grade')


class AnnouncementForm(FlaskForm):
    """Announcement creation form."""
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], validators=[DataRequired()])
    submit = SubmitField('Post Announcement')


class SearchForm(FlaskForm):
    """General search form."""
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')


class PasswordResetRequestForm(FlaskForm):
    """Password reset request form."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class PasswordResetForm(FlaskForm):
    """Password reset form."""
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')


class DepartmentForm(FlaskForm):
    """Department create/edit form."""
    code = StringField('Code', validators=[DataRequired(), Length(max=10)])
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Department')


class ConfirmDeleteForm(FlaskForm):
    """Simple confirmation form for deletions (CSRF-protected)."""
    submit = SubmitField('Delete')


class AdminUserEditForm(FlaskForm):
    """Admin user edit form."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=50)])
    roles = SelectMultipleField('Roles', choices=[], validators=[DataRequired()])
    is_active = BooleanField('Active')
    password = PasswordField('New Password', validators=[Optional(), Length(min=8)])
    password2 = PasswordField('Confirm New Password', validators=[Optional(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Save')
