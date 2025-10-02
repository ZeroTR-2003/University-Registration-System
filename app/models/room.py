"""Room and Building models."""

from app.models import db, BaseModel


class Building(BaseModel):
    """Building model."""
    __tablename__ = 'buildings'
    
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200))
    floors = db.Column(db.Integer)
    
    # Relationships
    rooms = db.relationship('Room', back_populates='building', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Building {self.code}>'


class Room(BaseModel):
    """Room model for course locations."""
    __tablename__ = 'rooms'
    
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    room_number = db.Column(db.String(20), nullable=False)
    floor = db.Column(db.Integer)
    capacity = db.Column(db.Integer, nullable=False)
    room_type = db.Column(db.String(50))  # Lecture Hall, Lab, Seminar Room
    
    # Equipment
    has_projector = db.Column(db.Boolean, default=True)
    has_computers = db.Column(db.Boolean, default=False)
    has_whiteboard = db.Column(db.Boolean, default=True)
    equipment_list = db.Column(db.JSON)
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('building_id', 'room_number'),
    )
    
    # Relationships
    building = db.relationship('Building', back_populates='rooms')
    course_sections = db.relationship('CourseSection', back_populates='room')
    
    def __repr__(self):
        return f'<Room {self.building.code}-{self.room_number}>'
