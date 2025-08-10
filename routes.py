from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func, desc, asc
from datetime import datetime, date, timedelta
import json

from app import db
from models import *
from forms import *


main = Blueprint('main', __name__)

@main.route('/')
@login_required
def dashboard():
    lead_form = LeadForm()
    lead_form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    meeting_form = MeetingForm()
    meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    # Dashboard statistics
    total_leads = Lead.query.count()
    total_students = Student.query.count()
    total_courses = Course.query.filter_by(is_active=True).count()
    
    # Recent leads
    recent_leads = Lead.query.order_by(desc(Lead.created_at)).limit(5).all()
    
    # Pipeline data
    pipeline_data = db.session.query(
        Lead.status, func.count(Lead.id)
    ).group_by(Lead.status).all()
    
    # Monthly revenue
    monthly_revenue = db.session.query(
        func.sum(Student.fee_paid)
    ).filter(
        Student.enrollment_date >= date.today().replace(day=1)
    ).scalar() or 0
    
    return render_template('index.html',
                         total_leads=total_leads,
                         total_students=total_students,
                         total_courses=total_courses,
                         recent_leads=recent_leads,
                         pipeline_data=pipeline_data,
                         monthly_revenue=monthly_revenue,
                         lead_form=lead_form,
                         meeting_form=meeting_form)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))
        flash('Invalid username or password', 'error')
    
    return render_template('login.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

@main.route('/leads')
@login_required
def leads():
    lead_form = LeadForm()
    lead_form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    meeting_form = MeetingForm()
    meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    course_filter = request.args.get('course', '')
    
    query = Lead.query
    
    if search:
        query = query.filter(
            (Lead.name.contains(search)) |
            (Lead.phone.contains(search)) |
            (Lead.email.contains(search))
        )
    
    if status_filter:
        query = query.filter(Lead.status == status_filter)
    
    if course_filter:
        query = query.filter(Lead.course_interest_id == course_filter)
    
    leads_pagination = query.order_by(desc(Lead.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    courses = Course.query.filter_by(is_active=True).all()
    statuses = ['New', 'Contacted', 'Interested', 'Quoted', 'Converted', 'Lost']
    
    return render_template('leads.html',
                         leads=leads_pagination.items,
                         pagination=leads_pagination,
                         courses=courses,
                         statuses=statuses,
                         search=search,
                         status_filter=status_filter,
                         course_filter=course_filter,
                         lead_form=lead_form,
                         meeting_form=meeting_form)

@main.route('/leads/add', methods=['GET', 'POST'])
@login_required
def add_lead():
    form = LeadForm()
    
    # Debug: Check if courses exist
    all_courses = Course.query.all()
    active_courses = Course.query.filter_by(is_active=True).all()
    print(f"Total courses: {len(all_courses)}")
    print(f"Active courses: {len(active_courses)}")
    for course in active_courses:
        print(f"Course: {course.id} - {course.name} - Active: {course.is_active}")
    
    form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in active_courses]
    
    if form.validate_on_submit():
        lead = Lead(
            name=form.name.data,
            phone=form.phone.data,
            whatsapp=form.whatsapp.data,
            email=form.email.data,
            course_interest_id=form.course_interest_id.data if form.course_interest_id.data != 0 else None,
            lead_source=form.lead_source.data,
            status=form.status.data,
            quoted_amount=form.quoted_amount.data or 0.0,
            next_followup_date=form.next_followup_date.data,
            followup_type=form.followup_type.data,
            comments=form.comments.data,
            created_by_id=current_user.id
        )
        db.session.add(lead)
        db.session.commit()
        flash('Lead added successfully!', 'success')
        return redirect(url_for('main.leads'))
    
    return render_template('modals/lead_modal.html', form=form, title='Add New Lead')

@main.route('/leads/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(id):
    lead = Lead.query.get_or_404(id)
    form = LeadForm(obj=lead)
    form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        form.populate_obj(lead)
        if form.course_interest_id.data == 0:
            lead.course_interest_id = None
        db.session.commit()
        flash('Lead updated successfully!', 'success')
        return redirect(url_for('main.leads'))
    
    return render_template('modals/lead_modal.html', form=form, lead=lead, title='Edit Lead')

@main.route('/leads/<int:id>/convert', methods=['POST'])
@login_required
def convert_lead(id):
    lead = Lead.query.get_or_404(id)
    
    if lead.course_interest_id is None:
        flash('Please select a course before converting the lead.', 'error')
        return redirect(url_for('main.leads'))
    
    student = Student(
        lead_id=lead.id,
        name=lead.name,
        phone=lead.phone,
        email=lead.email,
        course_id=lead.course_interest_id,
        total_fee=lead.course_interest.price,
        enrollment_date=date.today()
    )
    
    lead.status = 'Converted'
    
    db.session.add(student)
    db.session.commit()
    
    flash(f'Lead {lead.name} converted to student successfully!', 'success')
    return redirect(url_for('main.students'))

@main.route('/pipeline')
@login_required
def pipeline():
    lead_form = LeadForm()
    lead_form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    meeting_form = MeetingForm()
    meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    # Get pipeline data grouped by status
    pipeline_data = db.session.query(
        Lead.status,
        func.count(Lead.id).label('count'),
        func.sum(Lead.quoted_amount).label('total_value')
    ).group_by(Lead.status).all()
    
    # Convert to dictionary for easier template usage
    pipeline_dict = {}
    for status, count, total_value in pipeline_data:
        pipeline_dict[status] = {
            'count': count,
            'total_value': total_value or 0
        }
    
    # Ensure all statuses are represented
    statuses = ['New', 'Contacted', 'Interested', 'Quoted', 'Converted', 'Lost']
    for status in statuses:
        if status not in pipeline_dict:
            pipeline_dict[status] = {'count': 0, 'total_value': 0}
    
    # Get leads for each status
    leads_by_status = {}
    for status in statuses:
        leads_by_status[status] = Lead.query.filter_by(status=status).all()
    
    return render_template('pipeline.html',
                         pipeline_data=pipeline_dict,
                         leads_by_status=leads_by_status,
                         statuses=statuses,
                         lead_form=lead_form,
                         meeting_form=meeting_form)

@main.route('/meetings')
@login_required
def meetings():
    today = date.today()
    start_of_month = today.replace(day=1)
    
    week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    week_end = datetime.combine(week_start + timedelta(days=6), datetime.max.time())
    
    meetings = Meeting.query.filter(
        Meeting.meeting_date >= start_of_month
    ).order_by(Meeting.meeting_date).all()
    
    # Convert meetings to JSON-serializable list of dicts
    meetings_data = [
        {
            'id': m.id,
            'title': m.title,
            'meeting_date': m.meeting_date.isoformat(),  # Convert to ISO string
            'meeting_type': m.meeting_type,
            'duration': m.duration,
            'status': m.status,
            'lead': {'name': m.lead.name} if m.lead else None,
            'student': {'name': m.student.name} if m.student else None,
            # Add other fields if needed (e.g., agenda, location)
        } for m in meetings
    ]
    
    current_date = today.strftime('%B %Y')
    
    meeting_form = MeetingForm()
    meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    return render_template('meetings.html',
                         meetings=meetings,  # Keep the original for Jinja loops
                         meetings_data=meetings_data,  # Serialized for JS
                         current_date=current_date,
                         week_start=week_start,
                         week_end=week_end,
                         today=today,
                         meeting_form=meeting_form)

@main.route('/meetings/add', methods=['GET', 'POST'])
@login_required
def add_meeting():
    form = MeetingForm()
    
    # Populate choices
    form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    if form.validate_on_submit():
        meeting = Meeting(
            title=form.title.data,
            meeting_type=form.meeting_type.data,
            meeting_date=datetime.combine(form.meeting_date.data, datetime.min.time()),
            duration=form.duration.data,
            meeting_link=form.meeting_link.data,
            location=form.location.data,
            agenda=form.agenda.data,
            created_by_id=current_user.id,
            email_reminder=form.email_reminder.data,
            sms_reminder=form.sms_reminder.data,
            reminder_time=int(form.reminder_time.data) if form.reminder_time.data else None
        )
        
        if form.lead_id.data != 0:
            meeting.lead_id = form.lead_id.data
        if form.student_id.data != 0:
            meeting.student_id = form.student_id.data
            
        db.session.add(meeting)
        db.session.commit()
        flash('Meeting scheduled successfully!', 'success')
        return redirect(url_for('main.meetings'))
    
    return render_template('modals/meeting_modal.html', form=form, title='Schedule Meeting')

@main.route('/courses')
@login_required
def courses():
    courses = Course.query.order_by(Course.name).all()
    return render_template('courses.html', courses=courses)

@main.route('/courses/add', methods=['GET', 'POST'])
@login_required
def add_course():
    form = CourseForm()
    
    if form.validate_on_submit():
        # Generate slug from name
        slug = form.name.data.lower().replace(' ', '-').replace('/', '-')
        
        course = Course(
            name=form.name.data,
            slug=slug,
            description=form.description.data,
            price=form.price.data,
            duration=form.duration.data,
            duration_type=form.duration_type.data,
            category=form.category.data,
            max_students=form.max_students.data or 20,
            is_active=form.is_active.data
        )
        
        db.session.add(course)
        db.session.commit()
        flash('Course added successfully!', 'success')
        return redirect(url_for('main.courses'))
    
    # Change this line to render a full page instead of modal
    return render_template('add_course.html', form=form, title='Add New Course')

# Enhanced Student Routes

@main.route('/students')
@login_required
def students():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    course_filter = request.args.get('course', '')
    status_filter = request.args.get('status', '')
    
    query = Student.query
    
    if search:
        query = query.filter(
            (Student.name.contains(search)) |
            (Student.phone.contains(search)) |
            (Student.email.contains(search))
        )
    
    if course_filter:
        query = query.filter(Student.course_id == course_filter)
    
    if status_filter:
        query = query.filter(Student.status == status_filter)
    
    students_pagination = query.order_by(desc(Student.enrollment_date)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    courses = Course.query.filter_by(is_active=True).all()
    statuses = ['Active', 'Completed', 'Dropped', 'Suspended']
    form = StudentForm()
    form.course_id.choices = [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    return render_template('students.html',
                         students=students_pagination.items,
                         pagination=students_pagination,
                         courses=courses,
                         statuses=statuses,
                         search=search,
                         course_filter=course_filter,
                         status_filter=status_filter,
                        form=form)

@main.route('/student-management')
@login_required  
def student_management():
    students = Student.query.order_by(desc(Student.enrollment_date)).all()
    form = StudentForm()
    form.course_id.choices = [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    return render_template('student_form.html', students=students, form=form)

@main.route('/students/add', methods=['POST'])
@login_required
def add_student():
    form = StudentForm()
    form.course_id.choices = [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        import json
        student = Student(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            country_code=form.country_code.data,
            phone=form.phone.data,
            email=form.email.data,
            course_id=form.course_id.data,
            schedule_days=form.schedule_days.data,
            schedule_time=form.schedule_time.data,
            total_fee=form.total_fee.data,
            fee_paid=form.fee_paid.data or 0.0,
            payment_plan=form.payment_plan.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            batch_name=form.batch_name.data
        )
        db.session.add(student)
        db.session.commit()
        flash('Student added successfully!', 'success')
    
    return redirect(url_for('main.student_management'))

@main.route('/students/<int:id>')
@login_required
def view_student(id):
    student = Student.query.get_or_404(id)
    return render_template('student_detail.html', student=student)

@main.route('/students/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    form = StudentForm(obj=student)
    form.course_id.choices = [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        form.populate_obj(student)
        db.session.commit()
        flash('Student updated successfully!', 'success')
        return redirect(url_for('main.student_management'))
    
    return render_template('student_edit.html', form=form, student=student)

@main.route('/students/<int:id>/payments')
@login_required
def student_payments(id):
    student = Student.query.get_or_404(id)
    return render_template('student_payments.html', student=student)


@main.route('/corporate')
@login_required
def corporate():
    form = CorporateTrainingForm()
    form.course_names.choices = [(str(c.id), c.name) for c in Course.query.filter_by(is_active=True).all()]
    corporate_trainings = CorporateTraining.query.order_by(desc(CorporateTraining.created_at)).all()

    # Preprocess corporate trainings to include course names
    corporate_trainings_data = []
    for training in corporate_trainings:
        course_names = []
        if training.course_names:  # Check if course_names is not None
            try:
                course_ids = json.loads(training.course_names)
                courses = Course.query.filter(Course.id.in_(course_ids)).all()
                course_names = [course.name for course in courses]
            except json.JSONDecodeError:
                course_names = ["Invalid course data"]
        training_data = {
            'id': training.id,
            'company_name': training.company_name,
            'contact_person': training.contact_person_name,  # Changed to match model field
            'contact_email': training.contact_person_email,
            'contact_phone': training.contact_person_phone,
            'industry': training.industry,
            'company_size': training.company_size,
            'course_names': course_names,  # List of course names
            'trainee_count': training.trainee_count,
            'training_mode': training.training_mode,
            'deal_value': training.deal_value,
            'status': training.status,
            'created_at': training.created_at,
            'budget_range': training.budget_range,
            'special_requirements': training.special_requirements
        }
        corporate_trainings_data.append(training_data)

    return render_template('corporate.html', corporate_trainings=corporate_trainings_data, form=form)

@main.route('/corporate/add', methods=['GET', 'POST'])
@login_required
def add_corporate():
    form = CorporateTrainingForm()
    form.course_names.choices = [(str(c.id), c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        import json
        corporate = CorporateTraining(
            company_name=form.company_name.data,
            location=form.location.data,
            contact_person_name=form.contact_person_name.data,
            contact_person_email=form.contact_person_email.data,
            contact_person_country_code=form.contact_person_country_code.data,
            contact_person_phone=form.contact_person_phone.data,
            industry=form.industry.data,
            company_size=form.company_size.data,
            course_names=json.dumps(form.course_names.data) if form.course_names.data else None,
            trainee_count=form.trainee_count.data,
            training_mode=form.training_mode.data,
            quotation_amount=form.quotation_amount.data or 0.0,
            expected_start_date=form.expected_start_date.data,
            budget_range=form.budget_range.data,
            special_requirements=form.special_requirements.data,
            created_by_id=current_user.id
        )
        
        db.session.add(corporate)
        db.session.commit()
        flash('Corporate training inquiry added successfully!', 'success')
        return redirect(url_for('main.corporate'))
    
    return render_template('corporate.html', form=form, corporate_trainings=CorporateTraining.query.order_by(desc(CorporateTraining.created_at)).all())

@main.route('/messages')
@login_required
def messages():
    templates = MessageTemplate.query.order_by(MessageTemplate.name).all()
    template_form = MessageTemplateForm()
    leads = Lead.query.all()
    courses = Course.query.filter_by(is_active=True).all()
    return render_template('messages.html', templates=templates, template_form=template_form, leads=leads, courses=courses)

# Message Template Routes
@main.route('/messages/add', methods=['POST'])
@login_required
def add_template():
    form = MessageTemplateForm()
    if form.validate_on_submit():
        template = MessageTemplate(
            name=form.name.data,
            category=form.category.data,
            subject=form.subject.data,
            content=form.content.data,
            message_type=form.message_type.data,
            is_active=form.is_active.data
        )
        db.session.add(template)
        db.session.commit()
        flash('Message template added successfully!', 'success')
    return redirect(url_for('main.messages'))

@main.route('/messages/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_template(id):
    template = MessageTemplate.query.get_or_404(id)
    form = MessageTemplateForm(obj=template)
    if form.validate_on_submit():
        form.populate_obj(template)
        db.session.commit()
        flash('Template updated successfully!', 'success')
        return redirect(url_for('main.messages'))
    return render_template('messages.html', template_form=form, template=template)

@main.route('/messages/<int:id>/delete')
@login_required
def delete_template(id):
    template = MessageTemplate.query.get_or_404(id)
    db.session.delete(template)
    db.session.commit()
    flash('Template deleted successfully!', 'success')
    return redirect(url_for('main.messages'))

@main.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    template_id = request.form.get('template_id')
    lead_ids = request.form.getlist('lead_ids')
    course_id = request.form.get('course_id')
    
    template = MessageTemplate.query.get_or_404(template_id)
    template.usage_count += 1
    db.session.commit()
    
    # Here you would implement actual message sending logic
    flash(f'Message sent to {len(lead_ids)} recipients!', 'success')
    return redirect(url_for('main.messages'))

@main.route('/reports')
@login_required
def reports():
    # Date range handling
    default_date_from = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    default_date_to = date.today().strftime('%Y-%m-%d')
    date_from = request.args.get('date_from', default_date_from)
    date_to = request.args.get('date_to', default_date_to)

    # Monthly leads
    monthly_leads = Lead.query.filter(
        Lead.created_at.between(date_from, date_to)
    ).all()

    # Conversion by source
    conversion_by_source = db.session.query(
        Lead.lead_source,
        func.count(Lead.id).label('total'),
        func.sum(db.cast(Lead.status == 'Converted', db.Integer)).label('converted')
    ).filter(
        Lead.created_at.between(date_from, date_to)
    ).group_by(Lead.lead_source).all()

    # Course popularity
    course_popularity = db.session.query(
        Course.name,
        func.count(Student.id).label('enrollments')
    ).join(Student).filter(
        Student.enrollment_date.between(date_from, date_to)
    ).group_by(Course.name).all()

    # Monthly lead trends (fixed for MySQL)
    monthly_trends = db.session.query(
        func.date_format(Lead.created_at, '%Y-%m').label('month'),
        func.count(Lead.id).label('count')
    ).group_by(func.date_format(Lead.created_at, '%Y-%m')).limit(12).all()

    return render_template('reports.html',
                         monthly_leads=monthly_leads,
                         conversion_by_source=conversion_by_source,
                         course_popularity=course_popularity,
                         monthly_trends=monthly_trends,
                         date_from=date_from,
                         date_to=date_to)

# Settings Routes - Replace the existing one
@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    form = SettingsForm()
    
    # Load current settings
    settings_dict = {}
    for setting in SystemSettings.query.all():
        settings_dict[setting.setting_key] = setting.setting_value
    
    if form.validate_on_submit():
        # Update or create settings
        for field in form:
            if field.name != 'csrf_token' and field.data:
                setting = SystemSettings.query.filter_by(setting_key=field.name).first()
                if setting:
                    setting.setting_value = str(field.data)
                else:
                    setting = SystemSettings(
                        setting_key=field.name,
                        setting_value=str(field.data),
                        setting_type='string'
                    )
                    db.session.add(setting)
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('main.settings'))
    
    # Pre-populate form with current settings
    for field in form:
        if field.name in settings_dict:
            field.data = settings_dict[field.name]
    
    return render_template('settings.html', form=form)

# API endpoints for AJAX operations
@main.route('/api/leads/<int:id>/status', methods=['POST'])
@login_required
def update_lead_status(id):
    lead = Lead.query.get_or_404(id)
    new_status = request.json.get('status')
    
    if new_status in ['New', 'Contacted', 'Interested', 'Quoted', 'Converted', 'Lost']:
        lead.status = new_status
        db.session.commit()
        return jsonify({'success': True, 'message': 'Status updated successfully'})
    
    return jsonify({'success': False, 'message': 'Invalid status'}), 400

@main.route('/api/pipeline/data')
@login_required
def pipeline_api_data():
    pipeline_data = db.session.query(
        Lead.status,
        func.count(Lead.id).label('count'),
        func.sum(Lead.quoted_amount).label('total_value')
    ).group_by(Lead.status).all()
    
    result = {}
    for status, count, total_value in pipeline_data:
        result[status] = {
            'count': count,
            'total_value': float(total_value or 0)
        }
    
    return jsonify(result)

# Corporate Training Routes  
@main.route('/corporate-leads')
@login_required
def corporate_leads():
    leads = CorporateTraining.query.order_by(desc(CorporateTraining.created_at)).all()
    form = CorporateTrainingForm()
    form.course_names.choices = [(str(c.id), c.name) for c in Course.query.filter_by(is_active=True).all()]
    return render_template('corporate_leads.html', corporate_leads=leads, form=form)

@main.route('/corporate-leads/add', methods=['POST'])
@login_required
def add_corporate_lead():
    form = CorporateTrainingForm()
    form.course_names.choices = [(str(c.id), c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        import json
        lead = CorporateTraining(
            company_name=form.company_name.data,
            location=form.location.data,
            contact_person_name=form.contact_person_name.data,
            contact_person_email=form.contact_person_email.data,
            contact_person_country_code=form.contact_person_country_code.data,
            contact_person_phone=form.contact_person_phone.data,
            industry=form.industry.data,
            company_size=form.company_size.data,
            course_names=json.dumps([form.course_names.data]) if form.course_names.data else None,
            trainee_count=form.trainee_count.data,
            training_mode=form.training_mode.data,
            quotation_amount=form.quotation_amount.data or 0.0,
            expected_start_date=form.expected_start_date.data,
            budget_range=form.budget_range.data,
            special_requirements=form.special_requirements.data,
            created_by_id=current_user.id
        )
        db.session.add(lead)
        db.session.commit()
        flash('Corporate lead added successfully!', 'success')
    
    return redirect(url_for('main.corporate_leads'))

@main.route('/corporate-leads/<int:id>')
@login_required
def view_corporate_lead(id):
    lead = CorporateTraining.query.get_or_404(id)
    course_names_list = []
    if lead.course_names:
        try:
            course_ids = json.loads(lead.course_names)
            courses = Course.query.filter(Course.id.in_(course_ids)).all()
            course_names_list = [course.name for course in courses]
        except json.JSONDecodeError:
            course_names_list = []
    return render_template('corporate_lead_detail.html', lead=lead, course_names_list=course_names_list)

@main.route('/corporate-leads/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_corporate_lead(id):
    lead = CorporateTraining.query.get_or_404(id)
    form = CorporateTrainingForm(obj=lead)
    form.course_names.choices = [(str(c.id), c.name) for c in Course.query.filter_by(is_active=True).all()]

    # Pre-populate course_names from JSON
    if lead.course_names:
        try:
            form.course_names.data = json.loads(lead.course_names)
        except json.JSONDecodeError:
            form.course_names.data = []
    
    if form.validate_on_submit():
        form.populate_obj(lead)
        # Convert course_names to JSON string
        lead.course_names = json.dumps(form.course_names.data) if form.course_names.data else None
        db.session.commit()
        flash('Corporate lead updated successfully!', 'success')
        return redirect(url_for('main.corporate_leads'))
    
    return render_template('corporate_lead_edit.html', form=form, lead=lead)

@main.route('/corporate-leads/<int:id>/delete')
@login_required
def delete_corporate_lead(id):
    lead = CorporateTraining.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    flash('Corporate lead deleted successfully!', 'success')
    return redirect(url_for('main.corporate_leads'))
