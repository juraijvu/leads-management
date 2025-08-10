from app import db
from flask_login import UserMixin
from datetime import datetime, date
from sqlalchemy import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    whatsapp = db.Column(db.String(20))
    email = db.Column(db.String(120))
    course_interest_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    lead_source = db.Column(db.String(50))
    status = db.Column(db.String(20), default='New')  # New, Contacted, Interested, Quoted, Converted, Lost
    quoted_amount = db.Column(db.Float, default=0.0)
    last_contact_date = db.Column(db.Date)
    next_followup_date = db.Column(db.Date)
    followup_type = db.Column(db.String(20))  # Call, Email, WhatsApp, Meeting
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    course_interest = db.relationship('Course', backref='interested_leads')
    created_by = db.relationship('User', backref='created_leads')
    interactions = db.relationship('LeadInteraction', backref='lead', lazy='dynamic')
    
    def __repr__(self):
        return f'<Lead {self.name}>'

class LeadInteraction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'), nullable=False)
    interaction_type = db.Column(db.String(20), nullable=False)  # Call, Email, WhatsApp, Meeting, Note
    content = db.Column(db.Text)
    interaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_important = db.Column(db.Boolean, default=False)
    
    created_by = db.relationship('User', backref='interactions')

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    duration = db.Column(db.String(50))  # e.g., "3 months", "6 weeks"
    duration_type = db.Column(db.String(20))  # weeks, months, days
    category = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    max_students = db.Column(db.Integer, default=20)
    key_points = db.Column(db.Text)  # JSON string of key points
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    students = db.relationship('Student', backref='course')
    # Removed: corporate_trainings = db.relationship('CorporateTraining', backref='course')
    
    def __repr__(self):
        return f'<Course {self.name}>'

class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    title = db.Column(db.String(200), nullable=False)
    meeting_type = db.Column(db.String(20), nullable=False)  # Online, Offline
    meeting_date = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, default=60)  # minutes
    status = db.Column(db.String(20), default='Scheduled')  # Scheduled, Completed, Cancelled, No Show
    meeting_link = db.Column(db.String(500))  # For online meetings
    location = db.Column(db.String(200))  # For offline meetings
    agenda = db.Column(db.Text)
    notes = db.Column(db.Text)
    reminder_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    email_reminder = db.Column(db.Boolean, default=False, nullable=False)
    sms_reminder = db.Column(db.Boolean, default=False, nullable=False)
    reminder_time = db.Column(db.Integer, nullable=True)  # Minutes before meeting
    
    # Relationships
    lead = db.relationship('Lead', backref='meetings')
    student = db.relationship('Student', backref='meetings')
    created_by = db.relationship('User', backref='created_meetings')

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id'))  # Original lead if converted
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    country_code = db.Column(db.String(5), default='+971')
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    schedule_days = db.Column(db.Text)  # JSON array of selected days
    schedule_time = db.Column(db.String(20))  # Time slot
    enrollment_date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='Active')  # Active, Completed, Dropped, Suspended
    fee_paid = db.Column(db.Float, default=0.0)
    total_fee = db.Column(db.Float, nullable=False)
    payment_plan = db.Column(db.String(50))  # Full, Installments
    progress_percentage = db.Column(db.Float, default=0.0)
    batch_name = db.Column(db.String(100))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"
    
    # Relationships
    original_lead = db.relationship('Lead', backref='converted_student')
    attendance_records = db.relationship('AttendanceRecord', backref='student')
    
    def __repr__(self):
        return f'<Student {self.name}>'

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # Present, Absent, Late
    notes = db.Column(db.Text)

class CorporateTraining(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    contact_person_name = db.Column(db.String(100), nullable=False)
    contact_person_email = db.Column(db.String(120), nullable=False)
    contact_person_country_code = db.Column(db.String(5), default='+971')
    contact_person_phone = db.Column(db.String(20), nullable=False)
    industry = db.Column(db.String(100))
    company_size = db.Column(db.String(50))
    course_names = db.Column(db.Text)  # JSON array of course IDs for multiple courses
    trainee_count = db.Column(db.Integer, nullable=False)
    training_mode = db.Column(db.String(20))  # Onsite, Online, Hybrid
    quotation_amount = db.Column(db.Float, default=0.0)
    expected_start_date = db.Column(db.Date)
    budget_range = db.Column(db.String(50))
    special_requirements = db.Column(db.Text)
    status = db.Column(db.String(20), default='Inquiry')  # Inquiry, Proposal, Negotiation, Confirmed, Completed
    deal_value = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    created_by = db.relationship('User', backref='corporate_leads')

class MessageTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))  # Welcome, Follow-up, Reminder, etc.
    subject = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20))  # Email, SMS, WhatsApp
    is_active = db.Column(db.Boolean, default=True)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_key = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.Text)
    setting_type = db.Column(db.String(20))  # string, number, boolean, json
    description = db.Column(db.String(200))