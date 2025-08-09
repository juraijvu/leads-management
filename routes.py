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
    
    # Monthly revenue (from converted students)
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
                         monthly_revenue=monthly_revenue)

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
                         course_filter=course_filter)

@main.route('/leads/add', methods=['GET', 'POST'])
@login_required
def add_lead():
    form = LeadForm()
    form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
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
                         statuses=statuses)

@main.route('/meetings')
@login_required
def meetings():
    # Get meetings for the current month
    today = date.today()
    start_of_month = today.replace(day=1)
    
    meetings = Meeting.query.filter(
        Meeting.meeting_date >= start_of_month
    ).order_by(Meeting.meeting_date).all()
    
    return render_template('meetings.html', meetings=meetings)

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
            created_by_id=current_user.id
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
    
    return render_template('modals/course_modal.html', form=form, title='Add New Course')

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
    
    return render_template('students.html',
                         students=students_pagination.items,
                         pagination=students_pagination,
                         courses=courses,
                         statuses=statuses,
                         search=search,
                         course_filter=course_filter,
                         status_filter=status_filter)

@main.route('/corporate')
@login_required
def corporate():
    corporate_trainings = CorporateTraining.query.order_by(desc(CorporateTraining.created_at)).all()
    return render_template('corporate.html', corporate_trainings=corporate_trainings)

@main.route('/corporate/add', methods=['GET', 'POST'])
@login_required
def add_corporate():
    form = CorporateTrainingForm()
    form.course_id.choices = [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        corporate = CorporateTraining(
            company_name=form.company_name.data,
            contact_person=form.contact_person.data,
            contact_email=form.contact_email.data,
            contact_phone=form.contact_phone.data,
            industry=form.industry.data,
            company_size=form.company_size.data,
            course_id=form.course_id.data,
            trainee_count=form.trainee_count.data,
            training_mode=form.training_mode.data,
            budget_range=form.budget_range.data,
            special_requirements=form.special_requirements.data,
            deal_value=form.deal_value.data or 0.0
        )
        
        db.session.add(corporate)
        db.session.commit()
        flash('Corporate training inquiry added successfully!', 'success')
        return redirect(url_for('main.corporate'))
    
    return render_template('corporate.html', form=form)

@main.route('/messages')
@login_required
def messages():
    templates = MessageTemplate.query.order_by(MessageTemplate.name).all()
    return render_template('messages.html', templates=templates)

@main.route('/reports')
@login_required
def reports():
    # Generate basic reports data
    
    # Monthly lead generation
    monthly_leads = db.session.query(
        func.strftime('%Y-%m', Lead.created_at).label('month'),
        func.count(Lead.id).label('count')
    ).group_by(func.strftime('%Y-%m', Lead.created_at)).limit(12).all()
    
    # Conversion rates by source
    conversion_by_source = db.session.query(
        Lead.lead_source,
        func.count(Lead.id).label('total'),
        func.sum(func.case([(Lead.status == 'Converted', 1)], else_=0)).label('converted')
    ).group_by(Lead.lead_source).all()
    
    # Course popularity
    course_popularity = db.session.query(
        Course.name,
        func.count(Student.id).label('enrollments')
    ).join(Student).group_by(Course.name).order_by(desc(func.count(Student.id))).all()
    
    return render_template('reports.html',
                         monthly_leads=monthly_leads,
                         conversion_by_source=conversion_by_source,
                         course_popularity=course_popularity)

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

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
