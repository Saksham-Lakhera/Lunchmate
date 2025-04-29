from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association table for matches (many-to-many relationship)
matches = db.Table('matches',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('matched_user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('status', db.Enum('pending', 'matched', 'unmatched', 'blocked', name='match_status_enum'), nullable=False, default='pending'),
    db.Column('matched_date', db.DateTime, nullable=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False)
)

# Notification table - stores user notifications
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    related_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('notifications', cascade='all, delete-orphan'))
    related_user = db.relationship('User', foreign_keys=[related_user_id])
    
    def __repr__(self):
        return f'<Notification {self.id} for user {self.user_id}>'

# User table - stores basic user information
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    photos = db.relationship('UserPhoto', backref='user', cascade='all, delete-orphan')
    lunch_preferences = db.relationship('LunchPreference', backref='user', uselist=False, cascade='all, delete-orphan')
    availability = db.relationship('UserAvailability', backref='user', cascade='all, delete-orphan')
    
    # Matching relationships
    matched_users = db.relationship(
        'User', 
        secondary=matches,
        primaryjoin=(matches.c.user_id == id),
        secondaryjoin=(matches.c.matched_user_id == id),
        backref=db.backref('matched_by', lazy='dynamic'),
        lazy='dynamic'
    )
    
    # Methods for password hashing
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

# UserProfile table - stores detailed user information
class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    university = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<UserProfile {self.first_name} {self.last_name}>'

# UserPhoto table - stores user photos
class UserPhoto(db.Model):
    __tablename__ = 'user_photos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    photo_path = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<UserPhoto {self.id} for user {self.user_id}>'

# LunchPreference table - stores user preferences for lunch
class LunchPreference(db.Model):
    __tablename__ = 'lunch_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    max_budget = db.Column(db.Float, nullable=True)
    preferred_group_size = db.Column(db.Integer, default=2, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    cuisine_preferences = db.relationship('CuisinePreference', backref='lunch_preference', cascade='all, delete-orphan')
    dietary_restrictions = db.relationship('DietaryRestriction', backref='lunch_preference', cascade='all, delete-orphan')
    
    @property
    def cuisines_string(self):
        if not self.cuisine_preferences:
            return ""
        return ", ".join([cp.cuisine_type for cp in self.cuisine_preferences])
    
    @property
    def restrictions_string(self):
        if not self.dietary_restrictions:
            return ""
        return ", ".join([dr.restriction_type for dr in self.dietary_restrictions])
    
    def __repr__(self):
        return f'<LunchPreference {self.id} for user {self.user_id}>'

# CuisinePreference table - stores user cuisine preferences
class CuisinePreference(db.Model):
    __tablename__ = 'cuisine_preferences'
    
    id = db.Column(db.Integer, primary_key=True)
    lunch_preference_id = db.Column(db.Integer, db.ForeignKey('lunch_preferences.id', ondelete='CASCADE'), nullable=False)
    cuisine_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('lunch_preference_id', 'cuisine_type', name='uix_user_cuisine_preference'),
    )
    
    def __repr__(self):
        return f'<CuisinePreference {self.cuisine_type} for preference {self.lunch_preference_id}>'
    
    def __str__(self):
        return self.cuisine_type

# DietaryRestriction table - stores user dietary restrictions
class DietaryRestriction(db.Model):
    __tablename__ = 'dietary_restrictions'
    
    id = db.Column(db.Integer, primary_key=True)
    lunch_preference_id = db.Column(db.Integer, db.ForeignKey('lunch_preferences.id', ondelete='CASCADE'), nullable=False)
    restriction_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('lunch_preference_id', 'restriction_type', name='uix_user_dietary_restriction'),
    )
    
    def __repr__(self):
        return f'<DietaryRestriction {self.restriction_type} for preference {self.lunch_preference_id}>'
    
    def __str__(self):
        return self.restriction_type

# UserAvailability table - stores user availability for lunch
class UserAvailability(db.Model):
    __tablename__ = 'user_availabilities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'day_of_week', 'start_time', 'end_time', name='uix_user_availability'),
    )
    
    def __repr__(self):
        return f'<UserAvailability day={self.day_of_week}, time={self.start_time}-{self.end_time}>'

# Restaurant table - stores information about restaurants
class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    cuisine_type = db.Column(db.String(100), nullable=True)
    price_range = db.Column(db.Integer, nullable=True)  # 1-5, with 5 being most expensive
    rating = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Restaurant {self.name}>'

# LunchMeeting table - stores scheduled lunch meetings
class LunchMeeting(db.Model):
    __tablename__ = 'lunch_meetings'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id', ondelete='SET NULL'), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum('scheduled', 'completed', 'canceled', name='meeting_status_enum'), default='scheduled', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    restaurant = db.relationship('Restaurant', backref=db.backref('lunch_meetings', lazy=True))
    participants = db.relationship('LunchMeetingParticipant', backref='lunch_meeting', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<LunchMeeting {self.id} at {self.scheduled_time}>'

# LunchMeetingParticipant table - many-to-many relationship between users and lunch meetings
class LunchMeetingParticipant(db.Model):
    __tablename__ = 'lunch_meeting_participants'
    
    id = db.Column(db.Integer, primary_key=True)
    lunch_meeting_id = db.Column(db.Integer, db.ForeignKey('lunch_meetings.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('confirmed', 'pending', 'declined', name='participant_status_enum'), default='pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('lunch_meeting_participants', lazy=True))
    
    __table_args__ = (
        db.UniqueConstraint('lunch_meeting_id', 'user_id', name='uix_lunch_meeting_participant'),
    )
    
    def __repr__(self):
        return f'<LunchMeetingParticipant meeting={self.lunch_meeting_id}, user={self.user_id}>'

# ConversationStarters table - stores AI-generated icebreaker questions
class ConversationStarter(db.Model):
    __tablename__ = 'conversation_starters'
    
    question_id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<ConversationStarter {self.question_id}: {self.question[:30]}...>' 