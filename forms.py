from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FloatField, DateField, IntegerField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange
from wtforms.widgets import TextArea
from models import Course, User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])

class LeadForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    whatsapp = StringField('WhatsApp', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    course_interest_id = SelectField('Course Interest', coerce=int, validators=[Optional()])
    lead_source = SelectField('Lead Source', choices=[
        ('Website', 'Website'),
        ('Social Media', 'Social Media'),
        ('Referral', 'Referral'),
        ('Advertisement', 'Advertisement'),
        ('Walk-in', 'Walk-in'),
        ('Other', 'Other')
    ], validators=[Optional()])
    status = SelectField('Status', choices=[
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Interested', 'Interested'),
        ('Quoted', 'Quoted'),
        ('Converted', 'Converted'),
        ('Lost', 'Lost')
    ], default='New')
    quoted_amount = FloatField('Quoted Amount', validators=[Optional(), NumberRange(min=0)])
    next_followup_date = DateField('Next Follow-up Date', validators=[Optional()])
    followup_type = SelectField('Follow-up Type', choices=[
        ('Call', 'Call'),
        ('Email', 'Email'),
        ('WhatsApp', 'WhatsApp'),
        ('Meeting', 'Meeting')
    ], validators=[Optional()])
    comments = TextAreaField('Comments', validators=[Optional()])

class CourseForm(FlaskForm):
    name = StringField('Course Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    duration = StringField('Duration', validators=[DataRequired(), Length(max=50)])
    duration_type = SelectField('Duration Type', choices=[
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')
    ], validators=[DataRequired()])
    category = StringField('Category', validators=[Optional(), Length(max=100)])
    max_students = IntegerField('Max Students', validators=[Optional(), NumberRange(min=1)])
    is_active = BooleanField('Active')

class MeetingForm(FlaskForm):
    lead_id = SelectField('Lead', coerce=int, validators=[Optional()])
    student_id = SelectField('Student', coerce=int, validators=[Optional()])
    title = StringField('Meeting Title', validators=[DataRequired(), Length(max=200)])
    meeting_type = SelectField('Meeting Type', choices=[
        ('Online', 'Online'),
        ('Offline', 'Offline')
    ], validators=[DataRequired()])
    meeting_date = DateField('Meeting Date', validators=[DataRequired()])
    duration = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=15, max=480)])
    meeting_link = StringField('Meeting Link', validators=[Optional(), Length(max=500)])
    location = StringField('Location', validators=[Optional(), Length(max=200)])
    agenda = TextAreaField('Agenda', validators=[Optional()])

class StudentForm(FlaskForm):
    name = StringField('Student Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    total_fee = FloatField('Total Fee', validators=[DataRequired(), NumberRange(min=0)])
    fee_paid = FloatField('Fee Paid', validators=[Optional(), NumberRange(min=0)])
    payment_plan = SelectField('Payment Plan', choices=[
        ('Full', 'Full Payment'),
        ('Installments', 'Installments')
    ], default='Full')
    batch_name = StringField('Batch Name', validators=[Optional(), Length(max=100)])
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])

class CorporateTrainingForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=200)])
    contact_person = StringField('Contact Person', validators=[DataRequired(), Length(max=100)])
    contact_email = StringField('Contact Email', validators=[DataRequired(), Email(), Length(max=120)])
    contact_phone = StringField('Contact Phone', validators=[DataRequired(), Length(max=20)])
    industry = StringField('Industry', validators=[Optional(), Length(max=100)])
    company_size = SelectField('Company Size', choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('500+', '500+ employees')
    ], validators=[Optional()])
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    trainee_count = IntegerField('Number of Trainees', validators=[DataRequired(), NumberRange(min=1)])
    training_mode = SelectField('Training Mode', choices=[
        ('Onsite', 'Onsite'),
        ('Online', 'Online'),
        ('Hybrid', 'Hybrid')
    ], validators=[DataRequired()])
    budget_range = StringField('Budget Range', validators=[Optional(), Length(max=50)])
    special_requirements = TextAreaField('Special Requirements', validators=[Optional()])
    deal_value = FloatField('Deal Value', validators=[Optional(), NumberRange(min=0)])

class MessageTemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('Welcome', 'Welcome'),
        ('Follow-up', 'Follow-up'),
        ('Reminder', 'Reminder'),
        ('Confirmation', 'Confirmation'),
        ('Thank You', 'Thank You'),
        ('Other', 'Other')
    ], validators=[DataRequired()])
    subject = StringField('Subject', validators=[Optional(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()], widget=TextArea())
    message_type = SelectField('Message Type', choices=[
        ('Email', 'Email'),
        ('SMS', 'SMS'),
        ('WhatsApp', 'WhatsApp')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)
