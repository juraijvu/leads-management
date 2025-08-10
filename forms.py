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
    email_reminder = BooleanField('Send Email Reminder', default=False)
    sms_reminder = BooleanField('Send SMS Reminder', default=False)
    reminder_time = SelectField('Reminder Time', choices=[
        ('', 'Select Reminder Time'),
        ('15', '15 minutes before'),
        ('30', '30 minutes before'),
        ('60', '1 hour before'),
        ('1440', '1 day before')
    ], validators=[Optional()])

# Enhanced Student Form
class StudentForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    country_code = SelectField('Country Code', choices=[
        ('+971', '+971 (UAE)'),
        ('+91', '+91 (India)'),
        ('+966', '+966 (Saudi Arabia)')
    ], default='+971')
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    schedule_days = SelectField('Schedule Days', choices=[
        ('weekdays', 'Weekdays (Mon-Fri)'),
        ('weekends', 'Weekends (Sat-Sun)')
    ], validators=[DataRequired()])
    schedule_time = SelectField('Schedule Time', choices=[
        ('09:00-11:00', '09:00 AM - 11:00 AM'),
        ('11:00-13:00', '11:00 AM - 01:00 PM'),
        ('14:00-16:00', '02:00 PM - 04:00 PM'),
        ('16:00-18:00', '04:00 PM - 06:00 PM'),
        ('18:00-20:00', '06:00 PM - 08:00 PM')
    ], validators=[DataRequired()])
    total_fee = FloatField('Total Fee (AED)', validators=[DataRequired(), NumberRange(min=0)])
    fee_paid = FloatField('Fee Paid (AED)', validators=[Optional(), NumberRange(min=0)], default=0)
    payment_plan = SelectField('Payment Plan', choices=[
        ('Full Payment', 'Full Payment'),
        ('2 Installments', '2 Installments'),
        ('3 Installments', '3 Installments'),
        ('Monthly', 'Monthly Installments')
    ], default='Full Payment')
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    batch_name = StringField('Batch Name', validators=[Optional(), Length(max=100)])


class CorporateTrainingForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=200)])
    location = StringField('Location', validators=[DataRequired(), Length(max=200)])
    contact_person_name = StringField('Contact Person Name', validators=[DataRequired(), Length(max=100)])
    contact_person_email = StringField('Contact Person Email', validators=[DataRequired(), Email(), Length(max=120)])
    contact_person_country_code = SelectField('Contact Country Code', choices=[
        ('+971', '+971 (UAE)'),
        ('+91', '+91 (India)'),
        ('+1', '+1 (US/Canada)'),
        ('+44', '+44 (UK)'),
        ('+92', '+92 (Pakistan)'),
        ('+94', '+94 (Sri Lanka)'),
        ('+880', '+880 (Bangladesh)'),
        ('+966', '+966 (Saudi Arabia)'),
        ('+965', '+965 (Kuwait)'),
        ('+973', '+973 (Bahrain)'),
        ('+974', '+974 (Qatar)'),
        ('+968', '+968 (Oman)')
    ], default='+971')
    contact_person_phone = StringField('Contact Person Phone', validators=[DataRequired(), Length(max=20)])
    industry = StringField('Industry', validators=[Optional(), Length(max=100)])
    company_size = SelectField('Company Size', choices=[
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('201-500', '201-500 employees'),
        ('500+', '500+ employees')
    ], validators=[Optional()])
    course_names = SelectField('Course Names (Multiple)', coerce=str, validators=[Optional()])
    trainee_count = IntegerField('Number of Trainees', validators=[DataRequired(), NumberRange(min=1)])
    training_mode = SelectField('Training Mode', choices=[
        ('Onsite', 'Onsite'),
        ('Online', 'Online'),
        ('Hybrid', 'Hybrid')
    ], validators=[DataRequired()])
    quotation_amount = FloatField('Quotation Amount', validators=[Optional(), NumberRange(min=0)])
    expected_start_date = DateField('Expected Start Date', validators=[Optional()])
    budget_range = StringField('Budget Range', validators=[Optional(), Length(max=50)])
    special_requirements = TextAreaField('Special Requirements', validators=[Optional()])

# Message Template Form
class MessageTemplateForm(FlaskForm):
    name = StringField('Template Name', validators=[DataRequired(), Length(max=100)])
    category = SelectField('Category', choices=[
        ('Lead Follow-up', 'Lead Follow-up'),
        ('Course Information', 'Course Information'),
        ('Payment Reminder', 'Payment Reminder'),
        ('Welcome Message', 'Welcome Message'),
        ('Course Completion', 'Course Completion'),
        ('Corporate Training', 'Corporate Training')
    ], validators=[DataRequired()])
    subject = StringField('Subject', validators=[Optional(), Length(max=200)], 
                         description='For Email messages only')
    content = TextAreaField('Message Content', validators=[DataRequired()], 
                           description='Use variables: {name}, {phone}, {email}, {course_name}, {company_name}')
    message_type = SelectField('Message Type', choices=[
        ('SMS', 'SMS'),
        ('WhatsApp', 'WhatsApp'),
        ('Email', 'Email')
    ], default='SMS', validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)

class SendMessageForm(FlaskForm):
    template_id = SelectField('Message Template', coerce=int, validators=[DataRequired()])
    lead_ids = SelectField('Select Leads', coerce=str, validators=[Optional()])
    course_id = SelectField('Course', coerce=int, validators=[Optional()])
    custom_variables = TextAreaField('Custom Variables (JSON)', validators=[Optional()])

class SettingsForm(FlaskForm):
    # Company Settings
    company_name = StringField('Company Name', validators=[Optional(), Length(max=200)])
    company_email = StringField('Company Email', validators=[Optional(), Email(), Length(max=120)])
    company_phone = StringField('Company Phone', validators=[Optional(), Length(max=20)])
    company_address = TextAreaField('Company Address', validators=[Optional()])
    
    # Email Settings
    mail_server = StringField('Mail Server', validators=[Optional(), Length(max=100)])
    mail_port = IntegerField('Mail Port', validators=[Optional(), NumberRange(min=1, max=65535)])
    mail_username = StringField('Mail Username', validators=[Optional(), Email(), Length(max=120)])
    mail_password = PasswordField('Mail Password', validators=[Optional()])
    mail_use_tls = BooleanField('Use TLS', default=True)
    
    # Payment Gateway Settings
    vault_api_key = StringField('Vault Pay API Key', validators=[Optional(), Length(max=200)])
    vault_secret_key = StringField('Vault Pay Secret Key', validators=[Optional(), Length(max=200)])
    tabby_public_key = StringField('Tabby Public Key', validators=[Optional(), Length(max=200)])
    tabby_secret_key = StringField('Tabby Secret Key', validators=[Optional(), Length(max=200)])
    tamara_api_key = StringField('Tamara API Key', validators=[Optional(), Length(max=200)])
    tamara_secret_key = StringField('Tamara Secret Key', validators=[Optional(), Length(max=200)])
    
    # Default Settings
    default_currency = SelectField('Default Currency', choices=[
        ('AED', 'AED (UAE Dirham)'),
        ('USD', 'USD (US Dollar)'),
        ('EUR', 'EUR (Euro)'),
        ('GBP', 'GBP (British Pound)'),
        ('SAR', 'SAR (Saudi Riyal)')
    ], default='AED')
    default_country_code = SelectField('Default Country Code', choices=[
        ('+971', '+971 (UAE)'),
        ('+91', '+91 (India)'),
        ('+1', '+1 (US/Canada)'),
        ('+44', '+44 (UK)'),
        ('+92', '+92 (Pakistan)'),
        ('+94', '+94 (Sri Lanka)'),
        ('+880', '+880 (Bangladesh)'),
        ('+966', '+966 (Saudi Arabia)'),
        ('+965', '+965 (Kuwait)'),
        ('+973', '+973 (Bahrain)'),
        ('+974', '+974 (Qatar)'),
        ('+968', '+968 (Oman)')
    ], default='+971')


