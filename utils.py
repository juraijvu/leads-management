"""
Utility functions for Training Center CRM
"""
import os
import re
import uuid
from datetime import datetime, date, timedelta
from flask import current_app
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def generate_slug(text):
    """Generate a URL-friendly slug from text"""
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    text = re.sub(r'[-\s]+', '-', text)
    return text

def format_currency(amount):
    """Format amount as currency"""
    if amount is None:
        return "$0.00"
    return f"${amount:,.2f}"

def format_phone(phone):
    """Format phone number for display"""
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Format as (XXX) XXX-XXXX if 10 digits
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    
    return phone

def calculate_conversion_rate(total_leads, converted_leads):
    """Calculate conversion rate percentage"""
    if total_leads == 0:
        return 0
    return round((converted_leads / total_leads) * 100, 2)

def get_lead_status_color(status):
    """Get Bootstrap color class for lead status"""
    status_colors = {
        'New': 'primary',
        'Contacted': 'warning', 
        'Interested': 'info',
        'Quoted': 'secondary',
        'Converted': 'success',
        'Lost': 'danger'
    }
    return status_colors.get(status, 'secondary')

def get_meeting_status_color(status):
    """Get Bootstrap color class for meeting status"""
    status_colors = {
        'Scheduled': 'primary',
        'Completed': 'success',
        'Cancelled': 'danger',
        'No Show': 'warning'
    }
    return status_colors.get(status, 'secondary')

def allowed_file(filename, allowed_extensions=None):
    """Check if file has allowed extension"""
    if allowed_extensions is None:
        allowed_extensions = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif'}
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_folder='uploads'):
    """Save uploaded file and return filename"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid filename conflicts
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(datetime.now().timestamp())}{ext}"
        
        # Ensure upload directory exists
        upload_path = os.path.join(current_app.instance_path, upload_folder)
        os.makedirs(upload_path, exist_ok=True)
        
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)
        return filename
    return None

def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_next_business_day(start_date=None, days_ahead=1):
    """Get next business day (Monday-Friday)"""
    if start_date is None:
        start_date = date.today()
    
    next_day = start_date + timedelta(days=days_ahead)
    
    # If it's weekend, move to Monday
    while next_day.weekday() > 4:  # 5 = Saturday, 6 = Sunday
        next_day += timedelta(days=1)
    
    return next_day

def send_email(to_email, subject, body, html_body=None):
    """Send email using configured SMTP settings"""
    try:
        from app import mail
        from flask_mail import Message
        
        msg = Message(
            subject=subject,
            recipients=[to_email],
            body=body,
            html=html_body
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send email: {str(e)}")
        return False

def generate_invoice_number():
    """Generate unique invoice number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = str(uuid.uuid4())[:8].upper()
    return f"INV-{timestamp}-{random_suffix}"

def validate_email(email):
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def validate_phone(phone):
    """Validate phone number format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    # Check if it's 10 digits (US format)
    return len(digits) == 10

def calculate_bulk_discount(base_price, quantity, discount_tiers=None):
    """Calculate bulk discount based on quantity"""
    if discount_tiers is None:
        discount_tiers = [
            (10, 0.05),   # 5% discount for 10+ students
            (20, 0.10),   # 10% discount for 20+ students
            (50, 0.15),   # 15% discount for 50+ students
            (100, 0.20),  # 20% discount for 100+ students
        ]
    
    discount_rate = 0
    for min_qty, rate in sorted(discount_tiers, reverse=True):
        if quantity >= min_qty:
            discount_rate = rate
            break
    
    total_price = base_price * quantity
    discount_amount = total_price * discount_rate
    final_price = total_price - discount_amount
    
    return {
        'original_price': total_price,
        'discount_rate': discount_rate,
        'discount_amount': discount_amount,
        'final_price': final_price
    }

def get_financial_year_dates(year=None):
    """Get financial year start and end dates"""
    if year is None:
        year = date.today().year
    
    # Assuming financial year starts April 1st
    start_date = date(year, 4, 1)
    end_date = date(year + 1, 3, 31)
    
    return start_date, end_date

def format_duration(duration_value, duration_type):
    """Format duration for display"""
    if not duration_value or not duration_type:
        return ""
    
    duration_map = {
        'days': 'day' if duration_value == 1 else 'days',
        'weeks': 'week' if duration_value == 1 else 'weeks',
        'months': 'month' if duration_value == 1 else 'months'
    }
    
    unit = duration_map.get(duration_type, duration_type)
    return f"{duration_value} {unit}"

def create_notification(user_id, title, message, notification_type='info'):
    """Create a notification for a user"""
    # This would typically save to a notifications table
    # For now, we'll just log it
    current_app.logger.info(f"Notification for user {user_id}: {title} - {message}")
    return True

def get_time_greeting():
    """Get appropriate greeting based on current time"""
    current_hour = datetime.now().hour
    
    if 5 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 17:
        return "Good afternoon"
    elif 17 <= current_hour < 22:
        return "Good evening"
    else:
        return "Good night"

def truncate_text(text, max_length=50, suffix="..."):
    """Truncate text to specified length"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def get_progress_color(percentage):
    """Get color class based on progress percentage"""
    if percentage >= 80:
        return 'success'
    elif percentage >= 60:
        return 'info'
    elif percentage >= 40:
        return 'warning'
    else:
        return 'danger'

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def generate_student_id():
    """Generate unique student ID"""
    year = datetime.now().year
    timestamp = datetime.now().strftime("%m%d%H%M")
    return f"STU{year}{timestamp}"

def calculate_payment_schedule(total_amount, installments=1, start_date=None):
    """Calculate payment schedule for installments"""
    if start_date is None:
        start_date = date.today()
    
    if installments <= 1:
        return [{'amount': total_amount, 'due_date': start_date}]
    
    amount_per_installment = total_amount / installments
    schedule = []
    
    for i in range(installments):
        due_date = start_date + timedelta(days=i * 30)  # Monthly installments
        schedule.append({
            'amount': amount_per_installment,
            'due_date': due_date,
            'installment_number': i + 1
        })
    
    return schedule

class DateTimeUtils:
    """Utility class for date and time operations"""
    
    @staticmethod
    def get_week_dates(date_obj=None):
        """Get start and end dates of the week"""
        if date_obj is None:
            date_obj = date.today()
        
        start_of_week = date_obj - timedelta(days=date_obj.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        return start_of_week, end_of_week
    
    @staticmethod
    def get_month_dates(date_obj=None):
        """Get start and end dates of the month"""
        if date_obj is None:
            date_obj = date.today()
        
        start_of_month = date_obj.replace(day=1)
        
        # Get last day of month
        if date_obj.month == 12:
            end_of_month = date_obj.replace(year=date_obj.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_of_month = date_obj.replace(month=date_obj.month + 1, day=1) - timedelta(days=1)
        
        return start_of_month, end_of_month
    
    @staticmethod
    def is_business_day(date_obj):
        """Check if date is a business day (Monday-Friday)"""
        return date_obj.weekday() < 5

class ValidationUtils:
    """Utility class for validation functions"""
    
    @staticmethod
    def is_valid_url(url):
        """Validate URL format"""
        url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        return re.match(url_pattern, url) is not None
    
    @staticmethod
    def is_strong_password(password):
        """Check if password meets strength requirements"""
        if len(password) < 8:
            return False
        
        # Check for at least one uppercase, lowercase, digit, and special character
        patterns = [
            r'[A-Z]',      # Uppercase
            r'[a-z]',      # Lowercase
            r'\d',         # Digit
            r'[!@#$%^&*(),.?":{}|<>]'  # Special character
        ]
        
        return all(re.search(pattern, password) for pattern in patterns)
