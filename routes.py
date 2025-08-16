from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func, desc, asc
from datetime import datetime, date, timedelta
import json

from app import db
from models import *
from forms import *
import logging
from utils import create_payment_link, verify_payment_status

# Configure logging
logging.basicConfig(level=logging.DEBUG)

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def dashboard():
    lead_form = LeadForm()
    lead_form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    meeting_form = MeetingForm()
    meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    # Dashboard statistics - ROLE-BASED ACCESS
    if current_user.is_admin() or current_user.can_view_all_leads:
        total_leads = Lead.query.count()
        recent_leads = Lead.query.order_by(desc(Lead.created_at)).limit(5).all()
        today_followups = Lead.query.filter(Lead.next_followup_date == date.today()).order_by(Lead.followup_time).all()
        pipeline_data = {
            'New': Lead.query.filter_by(status='New').count(),
            'Contacted': Lead.query.filter_by(status='Contacted').count(),
            'Interested': Lead.query.filter_by(status='Interested').count(),
            'Quoted': Lead.query.filter_by(status='Quoted').count(),
            'Converted': Lead.query.filter_by(status='Converted').count(),
            'Lost': Lead.query.filter_by(status='Lost').count()
        }
    else:
        # USER SPECIFIC DATA for consultants
        total_leads = Lead.query.filter_by(created_by_id=current_user.id).count()
        recent_leads = Lead.query.filter_by(created_by_id=current_user.id).order_by(desc(Lead.created_at)).limit(5).all()
        today_followups = Lead.query.filter_by(created_by_id=current_user.id).filter(Lead.next_followup_date == date.today()).order_by(Lead.followup_time).all()
        pipeline_data = Lead.get_user_pipeline_data(current_user.id)
        
    total_students = Student.query.count()  # Students can be common
    total_courses = Course.query.filter_by(is_active=True).count()  # Courses are common
    
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
                         today_followups=today_followups,
                         pipeline_data=pipeline_data,
                         monthly_revenue=monthly_revenue,
                         lead_form=lead_form,
                         meeting_form=meeting_form,
                         lead=None)

@main.route('/api/leads/<int:id>', methods=['GET'])
@login_required
def get_lead(id):
    lead = Lead.query.get_or_404(id)
    
    # ROLE-BASED ACCESS CONTROL
    if not (current_user.is_admin() or lead.assigned_to == current_user.id):
        return jsonify({
            'success': False,
            'message': 'You can only view leads assigned to you!'
        }), 403
    
    return jsonify({
        'success': True,
        'lead': {
            'id': lead.id,
            'name': lead.name,
            'phone': lead.phone,
            'email': lead.email,
            'whatsapp': lead.whatsapp,
            'course_interest_id': lead.course_interest_id,
            'status': lead.status,
            'lead_source': lead.lead_source,
            'comments': lead.comments
        }
    })

@main.route('/leads/<int:lead_id>')
@login_required
def lead_detail(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    
    # ROLE-BASED ACCESS CONTROL
    if not (current_user.is_admin() or lead.assigned_to == current_user.id):
        flash('You can only view leads assigned to you!', 'error')
        return redirect(url_for('main.leads'))
    
    # Get all interactions for this lead
    interactions = LeadInteraction.query.filter_by(lead_id=lead_id).order_by(desc(LeadInteraction.interaction_date)).all()
    
    # Get all meetings for this lead
    meetings = Meeting.query.filter_by(lead_id=lead_id).order_by(desc(Meeting.meeting_date)).all()
    
    # Get all quotes for this lead
    quotes = LeadQuote.query.filter_by(lead_id=lead_id).order_by(desc(LeadQuote.created_at)).all()
    
    # Combine all activities and sort by date
    activities = []
    
    # Add interactions
    for interaction in interactions:
        activities.append({
            'type': 'interaction' if interaction.interaction_type != 'Quote Update' else 'quote-update' if interaction.interaction_type != 'Follow-up Update' else 'follow-up-update',
            'subtype': interaction.interaction_type,
            'date': interaction.interaction_date,
            'content': interaction.content,
            'created_by': interaction.created_by.username if interaction.created_by else 'System',
            'is_important': interaction.is_important,
            'data': interaction
        })
    
    # Add meetings
    for meeting in meetings:
        activities.append({
            'type': 'meeting',
            'subtype': meeting.status,
            'date': meeting.meeting_date,
            'content': f"{meeting.title} - {meeting.meeting_type}",
            'created_by': meeting.created_by.username if meeting.created_by else 'System',
            'is_important': False,
            'data': meeting
        })
    
    # Add quotes
    for quote in quotes:
        activities.append({
            'type': 'quote',
            'subtype': quote.status,
            'date': quote.created_at,
            'content': f"Quote for {quote.course.name} - {quote.currency} {quote.quoted_amount}",
            'created_by': quote.created_by.username if quote.created_by else 'System',
            'is_important': True,
            'data': quote
        })
    
    # Sort activities by date (newest first)
    activities.sort(key=lambda x: x['date'], reverse=True)
    
    # Create forms
    activity_form = ActivityForm()
    followup_form = LeadFollowupForm(obj=lead)
    
    # Get courses for quote form
    courses = Course.query.filter_by(is_active=True).all()
    
    return render_template('lead_detail_modern.html', 
                         lead=lead, 
                         activities=activities,
                         quotes=quotes,
                         meetings=meetings,
                         courses=courses,
                         activity_form=activity_form,
                         followup_form=followup_form)

@main.route('/leads/quote/<int:id>/update_amount', methods=['POST'])
@login_required
def update_quote_amount(id):
    quote = LeadQuote.query.get_or_404(id)
    
    # ROLE-BASED ACCESS CONTROL
    if not (current_user.is_admin() or quote.lead.assigned_to == current_user.id):
        return jsonify({
            'success': False,
            'message': 'You can only edit quotes for leads assigned to you!'
        }), 403

    quoted_amount = request.form.get('quoted_amount', type=float)
    if not quoted_amount or quoted_amount <= 0:
        return jsonify({
            'success': False,
            'message': 'Invalid quote amount. Please enter a positive number.'
        }), 400

    try:
        # Store old amount for logging
        old_amount = quote.quoted_amount
        
        # Update quote amount
        quote.quoted_amount = quoted_amount
        
        # Update lead's quoted_amount (if this is the latest quote)
        latest_quote = LeadQuote.query.filter_by(lead_id=quote.lead_id).order_by(desc(LeadQuote.created_at)).first()
        if latest_quote.id == quote.id:
            quote.lead.quoted_amount = quoted_amount
        
        # Log the change as an interaction
        interaction = LeadInteraction(
            lead_id=quote.lead_id,
            interaction_type='Quote Update',
            interaction_date=datetime.now(),
            content=f"Quote amount updated from {quote.currency} {old_amount} to {quote.currency} {quoted_amount}",
            created_by_id=current_user.id,
            is_important=True
        )
        
        db.session.add(interaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Quote amount updated successfully!'
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating quote amount: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating quote amount: {str(e)}'
        }), 500

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
    
    meeting_form = MeetingForm()
    meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    course_filter = request.args.get('course', '')
    
    # ROLE-BASED ACCESS CONTROL FOR LEADS
    if current_user.is_admin() or current_user.can_view_all_leads:
        query = Lead.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if search:
            query = query.filter(
                db.or_(
                    Lead.name.ilike(f'%{search}%'),
                    Lead.phone.ilike(f'%{search}%'),
                    Lead.email.ilike(f'%{search}%')
                )
            )
        if course_filter:
            query = query.filter_by(course_interest_id=course_filter)
    else:
        query = Lead.query.filter_by(assigned_to=current_user.id)
        if status_filter:
            query = query.filter_by(status=status_filter)
        if search:
            query = query.filter(
                db.or_(
                    Lead.name.ilike(f'%{search}%'),
                    Lead.phone.ilike(f'%{search}%'),
                    Lead.email.ilike(f'%{search}%')
                )
            )
        if course_filter:
            query = query.filter_by(course_interest_id=course_filter)
    
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
                         meeting_form=meeting_form,
                         lead=None)

@main.route('/leads/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(id):
    if id == 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'errors': ['Invalid lead ID.']
            }), 400
        flash('Invalid lead ID.', 'error')
        return redirect(url_for('main.leads'))
    
    lead = Lead.query.get_or_404(id)
    
    # ROLE-BASED ACCESS CONTROL
    if not (current_user.is_admin() or lead.assigned_to == current_user.id):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'errors': ['You can only edit leads assigned to you!']
            }), 403
        flash('You can only edit leads assigned to you!', 'error')
        return redirect(url_for('main.leads'))
    
    form = LeadForm(obj=lead)
    form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # DUPLICATE DETECTION - Check phone/WhatsApp across all users but exclude current lead
        existing_lead = Lead.check_duplicate(form.phone.data, form.whatsapp.data, exclude_id=lead.id)
        if existing_lead:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'errors': [f'Duplicate lead detected based on phone or WhatsApp number! Lead exists (Added by: {existing_lead.added_by_user.username if existing_lead.added_by_user else "Unknown"})']
                }), 400
            flash(f'Duplicate lead detected based on phone or WhatsApp number! Lead exists (Added by: {existing_lead.added_by_user.username if existing_lead.added_by_user else "Unknown"})', 'warning')
            return render_template('edit_lead.html', lead_form=form, lead=lead)
        
        try:
            form.populate_obj(lead)
            lead.course_interest_id = form.course_interest_id.data if form.course_interest_id.data != 0 else None
            # Handle assignment change by admin
            if current_user.is_admin() and form.assigned_to.data != 0:
                lead.assigned_to = form.assigned_to.data
            db.session.commit()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'Lead updated successfully!'
                })
            flash('Lead updated successfully!', 'success')
            return redirect(url_for('main.lead_detail', lead_id=lead.id))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating lead: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'errors': ['An error occurred while updating the lead. Please try again.']
                }), 500
            flash('An error occurred while updating the lead. Please try again.', 'error')
            return render_template('edit_lead.html', lead_form=form, lead=lead)
    
    # Handle form validation errors for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.method == 'POST':
        errors = []
        for field, field_errors in form.errors.items():
            for error in field_errors:
                errors.append(f"{field}: {error}")
        return jsonify({
            'success': False,
            'errors': errors or ['Invalid form data. Please check your inputs.']
        }), 400
    
    # For GET requests, render the edit page as a fallback
    meeting_form = MeetingForm()
    meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    return render_template('edit_lead.html', lead_form=form, lead=lead)

@main.route('/leads/add', methods=['POST'])
@login_required
def add_lead():
    form = LeadForm()
    # Set choices for course_interest_id
    form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        # DUPLICATE DETECTION - Check phone/WhatsApp across all users
        existing_lead = Lead.check_duplicate(form.phone.data, form.whatsapp.data)
        if existing_lead:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'errors': [f'Duplicate lead detected based on phone or WhatsApp number! Lead exists (Added by: {existing_lead.added_by_user.username if existing_lead.added_by_user else "Unknown"})']
                }), 400
            flash(f'Duplicate lead detected based on phone or WhatsApp number! Lead exists (Added by: {existing_lead.added_by_user.username if existing_lead.added_by_user else "Unknown"})', 'warning')
            return redirect(url_for('main.leads'))
        
        try:
            # Create new lead
            lead = Lead()
            form.populate_obj(lead)
            lead.course_interest_id = form.course_interest_id.data if form.course_interest_id.data != 0 else None
            lead.added_by = current_user.id
            
            # Handle assignment
            if current_user.is_admin() and form.assigned_to.data != 0:
                lead.assigned_to = form.assigned_to.data
            else:
                # Consultants create leads assigned to themselves
                lead.assigned_to = current_user.id
            
            db.session.add(lead)
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'message': 'Lead created successfully!',
                    'lead_id': lead.id
                })
            flash('Lead created successfully!', 'success')
            return redirect(url_for('main.lead_detail', lead_id=lead.id))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating lead: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': False,
                    'errors': ['An error occurred while creating the lead. Please try again.']
                }), 500
            flash('An error occurred while creating the lead. Please try again.', 'error')
            return redirect(url_for('main.leads'))
    
    # Handle form validation errors for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        errors = []
        for field, field_errors in form.errors.items():
            for error in field_errors:
                errors.append(f"{field}: {error}")
        return jsonify({
            'success': False,
            'errors': errors or ['Invalid form data. Please check your inputs.']
        }), 400
    
    flash('Please correct the form errors.', 'error')
    return redirect(url_for('main.leads'))

@main.route('/leads/bulk-assign', methods=['POST'])
@login_required
def bulk_assign_leads():
    # Only admins can perform bulk assignments
    if not current_user.is_admin():
        flash('Access denied. Only admins can perform bulk assignments.', 'error')
        return redirect(url_for('main.leads'))
    
    form = BulkAssignForm()
    if form.validate_on_submit():
        try:
            lead_ids = form.selected_leads.data.split(',') if form.selected_leads.data else []
            if not lead_ids:
                flash('No leads selected for assignment.', 'warning')
                return redirect(url_for('main.leads'))
            
            # Update selected leads
            updated_count = 0
            for lead_id in lead_ids:
                if lead_id.strip():
                    lead = Lead.query.get(int(lead_id.strip()))
                    if lead:
                        lead.assigned_to = form.assigned_to.data
                        updated_count += 1
            
            db.session.commit()
            flash(f'Successfully assigned {updated_count} leads to the selected consultant.', 'success')
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error in bulk assignment: {str(e)}")
            flash('An error occurred during bulk assignment. Please try again.', 'error')
    else:
        flash('Invalid form data. Please try again.', 'error')
    
    return redirect(url_for('main.leads'))

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

@main.route('/leads/<int:id>', methods=['GET'], endpoint='lead_detail_simple')
@login_required
def lead_detail_simple(id):
    lead = Lead.query.get_or_404(id)
    return render_template('lead_detail.html',
                         lead=lead)

@main.route('/leads/<int:id>/delete', methods=['GET'])
@login_required
def delete_lead(id):
    lead = Lead.query.get_or_404(id)
    db.session.delete(lead)
    db.session.commit()
    flash('Lead deleted successfully!', 'success')
    return redirect(url_for('main.leads'))

@main.route('/pipeline')
@login_required
def pipeline():
    lead_form = LeadForm()
    lead_form.course_interest_id.choices = [(0, 'Select Course')] + [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    meeting_form = MeetingForm()
    
    # ROLE-BASED ACCESS CONTROL FOR PIPELINE
    if current_user.is_admin() or current_user.can_view_all_leads:
        # Admin sees all leads
        pipeline_query = db.session.query(
            Lead.status,
            func.count(Lead.id).label('count'),
            func.sum(Lead.quoted_amount).label('total_value')
        )
        meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    else:
        # Consultants see only their own leads
        pipeline_query = db.session.query(
            Lead.status,
            func.count(Lead.id).label('count'),
            func.sum(Lead.quoted_amount).label('total_value')
        ).filter(Lead.created_by_id == current_user.id)
        meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted', Lead.created_by_id == current_user.id).all()]
    
    pipeline_data = pipeline_query.group_by(Lead.status).all()
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    pipeline_dict = {}
    for status, count, total_value in pipeline_data:
        pipeline_dict[status] = {
            'count': count,
            'total_value': total_value or 0
        }
    
    statuses = ['New', 'Contacted', 'Interested', 'Quoted', 'Converted', 'Lost']
    for status in statuses:
        if status not in pipeline_dict:
            pipeline_dict[status] = {'count': 0, 'total_value': 0}
    
    leads_by_status = {}
    for status in statuses:
        if current_user.is_admin() or current_user.can_view_all_leads:
            leads_by_status[status] = Lead.query.filter_by(status=status).all()
        else:
            leads_by_status[status] = Lead.query.filter_by(status=status, created_by_id=current_user.id).all()
    
    return render_template('pipeline.html',
                         pipeline_data=pipeline_dict,
                         leads_by_status=leads_by_status,
                         statuses=statuses,
                         lead_form=lead_form,
                         meeting_form=meeting_form,
                         lead=None)

@main.route('/meetings')
@login_required
def meetings():
    today = date.today()
    start_of_month = today.replace(day=1)
    
    week_start = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    week_end = datetime.combine(week_start + timedelta(days=6), datetime.max.time())
    
    # ROLE-BASED ACCESS CONTROL FOR MEETINGS
    if current_user.is_admin() or current_user.can_view_all_leads:
        # Admin sees all meetings
        meetings = Meeting.query.filter(
            Meeting.meeting_date >= start_of_month
        ).order_by(Meeting.meeting_date).all()
        
        # Admin can schedule meetings for any lead
        meeting_form = MeetingForm()
        meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    else:
        # Consultants see only their own meetings
        meetings = Meeting.query.filter(
            Meeting.meeting_date >= start_of_month,
            Meeting.created_by_id == current_user.id
        ).order_by(Meeting.meeting_date).all()
        
        # Consultants can only schedule meetings for their own leads
        meeting_form = MeetingForm()
        meeting_form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted', Lead.added_by == current_user.id).all()]
    
    meetings_data = [
        {
            'id': m.id,
            'title': m.title,
            'meeting_date': m.meeting_date.isoformat(),
            'meeting_type': m.meeting_type,
            'duration': m.duration,
            'status': m.status,
            'lead': {'name': m.lead.name} if m.lead else None,
            'student': {'name': m.student.name} if m.student else None,
        } for m in meetings
    ]
    
    current_date = today.strftime('%B %Y')
    meeting_form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    return render_template('meetings.html',
                         meetings=meetings,
                         meetings_data=meetings_data,
                         current_date=current_date,
                         week_start=week_start,
                         week_end=week_end,
                         today=today,
                         meeting_form=meeting_form)

@main.route('/meetings/add', methods=['GET', 'POST'])
@login_required
def add_meeting():
    form = MeetingForm()
    form.lead_id.choices = [(0, 'Select Lead')] + [(l.id, l.name) for l in Lead.query.filter(Lead.status != 'Converted').all()]
    form.student_id.choices = [(0, 'Select Student')] + [(s.id, s.name) for s in Student.query.all()]
    
    if form.validate_on_submit():
        meeting = Meeting(
            title=form.title.data,
            meeting_type=form.meeting_type.data,
            meeting_date=datetime.combine(form.meeting_date.data, form.meeting_time.data),
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
    
    return render_template('modals/meeting_modal.html', meeting_form=form, title='Schedule Meeting')

@main.route('/courses')
@login_required
def courses():
    courses = Course.query.order_by(Course.name).all()
    for course in courses:
        course.name = course.name.replace('&', '&amp;') if course.name else ''
        course.description = course.description.replace('&', '&amp;') if course.description else ''
        course.category = course.category.replace('&', '&amp;') if course.category else ''
        if course.key_points:
            try:
                key_points = json.loads(course.key_points)
                course.key_points = json.dumps([point.replace('&', '&amp;') for point in key_points])
            except json.JSONDecodeError:
                course.key_points = '[]'
    return render_template('courses.html', courses=courses)

@main.route('/api/courses')
@login_required
def get_courses():
    courses = Course.query.order_by(Course.name).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'description': c.description,
        'price': c.price,
        'duration': c.duration,
        'category': c.category,
        'is_active': c.is_active,
        'students': [{'id': s.id, 'name': s.name} for s in c.students],
        'max_students': c.max_students,
        'key_points': json.loads(c.key_points) if c.key_points else []
    } for c in courses])

@main.route('/courses/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_course(id):
    course = Course.query.get_or_404(id)
    form = CourseForm(obj=course)
    
    if form.validate_on_submit():
        form.populate_obj(course)
        course.slug = form.name.data.lower().replace(' ', '-').replace('/', '-')
        course.key_points = form.key_points.data if form.key_points.data else '[]'
        
        try:
            db.session.commit()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('main.courses'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating course: {str(e)}")
            flash('An error occurred while updating the course. Please try again.', 'error')
    
    return render_template('edit_course.html', form=form, course=course)

@main.route('/courses/add', methods=['GET', 'POST'])
@login_required
def add_course():
    form = CourseForm()
    
    if form.validate_on_submit():
        slug = form.name.data.lower().replace(' ', '-').replace('/', '-')
        
        # Validate and sanitize key_points
        key_points = form.key_points.data if form.key_points.data else '[]'
        try:
            json.loads(key_points)
        except json.JSONDecodeError:
            flash('Invalid key points format. Please provide a valid JSON array (e.g., ["point1", "point2"]).', 'error')
            return render_template('add_course.html', form=form, title='Add New Course')
        
        course = Course(
            name=form.name.data,
            slug=slug,
            description=form.description.data,
            price=form.price.data,
            duration=form.duration.data,
            duration_type=form.duration_type.data,
            category=form.category.data,
            max_students=form.max_students.data or 20,
            is_active=form.is_active.data,
            key_points=key_points
        )
        
        try:
            db.session.add(course)
            db.session.commit()
            flash('Course added successfully!', 'success')
            return redirect(url_for('main.courses'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding course: {str(e)}")
            flash('An error occurred while adding the course. Please try again.', 'error')
    
    return render_template('add_course.html', form=form, title='Add New Course')

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

    corporate_trainings_data = []
    for training in corporate_trainings:
        course_names = []
        if training.course_names:
            try:
                course_ids = json.loads(training.course_names)
                courses = Course.query.filter(Course.id.in_(course_ids)).all()
                course_names = [course.name for course in courses]
            except json.JSONDecodeError:
                course_names = ["Invalid course data"]
        training_data = {
            'id': training.id,
            'company_name': training.company_name,
            'contact_person': training.contact_person_name,
            'contact_email': training.contact_person_email,
            'contact_phone': training.contact_person_phone,
            'industry': training.industry,
            'company_size': training.company_size,
            'course_names': course_names,
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
    
    flash(f'Message sent to {len(lead_ids)} recipients!', 'success')
    return redirect(url_for('main.messages'))

@main.route('/api/templates/<int:id>', methods=['GET'])
@login_required
def get_template(id):
    template = MessageTemplate.query.get_or_404(id)
    return jsonify({
        'success': True,
        'template': {
            'id': template.id,
            'name': template.name,
            'category': template.category,
            'message_type': template.message_type,
            'subject': template.subject,
            'content': template.content,
            'is_active': template.is_active
        }
    })

@main.route('/reports')
@login_required
def reports():
    default_date_from = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
    date_from = request.args.get('date_from', default_date_from)
    date_to = request.args.get('date_to', date.today().strftime('%Y-%m-%d'))

    monthly_leads = Lead.query.filter(
        Lead.created_at.between(date_from, date_to)
    ).all()

    conversion_by_source = db.session.query(
        Lead.lead_source,
        func.count(Lead.id).label('total'),
        func.sum(db.cast(Lead.status == 'Converted', db.Integer)).label('converted')
    ).filter(
        Lead.created_at.between(date_from, date_to)
    ).group_by(Lead.lead_source).all()

    course_popularity = db.session.query(
        Course.name,
        func.count(Student.id).label('enrollments')
    ).join(Student).filter(
        Student.enrollment_date.between(date_from, date_to)
    ).group_by(Course.name).all()

    monthly_trends = db.session.query(
        func.date_format(Lead.created_at, '%Y-%m').label('month'),
        func.count(Lead.id).label('count')
    ).group_by(func.date_format(Lead.created_at, '%Y-%m')).order_by(func.date_format(Lead.created_at, '%Y-%m').desc()).limit(12).all()

    return render_template('reports.html',
                         monthly_leads=monthly_leads,
                         conversion_by_source=conversion_by_source,
                         course_popularity=course_popularity,
                         monthly_trends=monthly_trends,
                         date_from=date_from,
                         date_to=date_to)

@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Comprehensive settings management"""
    
    # Get all settings categories
    lead_sources = Setting.get_by_key('lead_source')
    lead_statuses = Setting.get_by_key('lead_status') 
    followup_types = Setting.get_by_key('followup_type')
    priority_levels = Setting.get_by_key('priority_level')
    meeting_types = Setting.get_by_key('meeting_type')
    
    # Get system settings
    system_settings = {}
    system_keys = ['company_name', 'company_email', 'company_phone', 'company_address', 
                   'default_currency', 'timezone', 'leads_per_page', 'auto_followup_days',
                   'email_notifications', 'sms_notifications']
    
    for key in system_keys:
        system_settings[key] = Setting.get_single_value(key, '')
    
    # Initialize forms
    setting_form = SettingForm()
    system_form = SystemSettingsForm()
    
    # Populate system form with current values
    system_form.company_name.data = system_settings.get('company_name', '')
    system_form.company_email.data = system_settings.get('company_email', '')
    system_form.company_phone.data = system_settings.get('company_phone', '')
    system_form.company_address.data = system_settings.get('company_address', '')
    system_form.default_currency.data = system_settings.get('default_currency', 'USD')
    system_form.timezone.data = system_settings.get('timezone', 'UTC')
    
    # Handle numeric fields with validation
    leads_per_page = system_settings.get('leads_per_page', '20')
    system_form.leads_per_page.data = int(leads_per_page) if leads_per_page and leads_per_page.isdigit() else 20
    
    auto_followup_days = system_settings.get('auto_followup_days', '3')
    system_form.auto_followup_days.data = int(auto_followup_days) if auto_followup_days and auto_followup_days.isdigit() else 3
    
    system_form.email_notifications.data = system_settings.get('email_notifications', 'true') == 'true'
    system_form.sms_notifications.data = system_settings.get('sms_notifications', 'false') == 'true'
    
    # Handle form submissions
    if request.method == 'POST':
        if 'save_system_settings' in request.form and system_form.validate_on_submit():
            # Update system settings
            system_updates = {
                'company_name': system_form.company_name.data,
                'company_email': system_form.company_email.data,
                'company_phone': system_form.company_phone.data,
                'company_address': system_form.company_address.data,
                'default_currency': system_form.default_currency.data,
                'timezone': system_form.timezone.data,
                'leads_per_page': str(system_form.leads_per_page.data),
                'auto_followup_days': str(system_form.auto_followup_days.data),
                'email_notifications': str(system_form.email_notifications.data).lower(),
                'sms_notifications': str(system_form.sms_notifications.data).lower()
            }
            
            for key, value in system_updates.items():
                setting = Setting.query.filter_by(key=key).first()
                if setting:
                    setting.value = value
                    setting.updated_at = datetime.utcnow()
                else:
                    new_setting = Setting(
                        key=key,
                        value=value,
                        display_name=key.replace('_', ' ').title(),
                        is_active=True
                    )
                    db.session.add(new_setting)
            
            db.session.commit()
            flash('System settings updated successfully!', 'success')
            return redirect(url_for('main.settings'))
            
        elif 'add_setting' in request.form and setting_form.validate_on_submit():
            # Add new setting
            new_setting = Setting(
                key=setting_form.key.data,
                value=setting_form.value.data,
                display_name=setting_form.display_name.data,
                description=setting_form.description.data,
                is_active=setting_form.is_active.data,
                sort_order=setting_form.sort_order.data
            )
            db.session.add(new_setting)
            db.session.commit()
            flash('Setting added successfully!', 'success')
            return redirect(url_for('main.settings'))
    
    return render_template('settings.html', 
                         lead_sources=lead_sources,
                         lead_statuses=lead_statuses,
                         followup_types=followup_types,
                         priority_levels=priority_levels,
                         meeting_types=meeting_types,
                         system_settings=system_settings,
                         setting_form=setting_form,
                         system_form=system_form)

@main.route('/settings/delete/<int:setting_id>', methods=['POST'])
@login_required
def delete_setting(setting_id):
    """Delete a setting"""
    if not (current_user.is_admin() or current_user.can_manage_settings):
        flash('Access denied. You do not have permission to manage settings.', 'error')
        return redirect(url_for('main.settings'))
    
    setting = Setting.query.get_or_404(setting_id)
    db.session.delete(setting)
    db.session.commit()
    flash(f'Setting "{setting.display_name}" deleted successfully!', 'success')
    return redirect(url_for('main.settings'))

@main.route('/settings/toggle/<int:setting_id>', methods=['POST'])
@login_required
def toggle_setting(setting_id):
    """Toggle setting active status"""
    if not (current_user.is_admin() or current_user.can_manage_settings):
        flash('Access denied. You do not have permission to manage settings.', 'error')
        return redirect(url_for('main.settings'))
    
    setting = Setting.query.get_or_404(setting_id)
    setting.is_active = not setting.is_active
    setting.updated_at = datetime.utcnow()
    db.session.commit()
    
    status = "activated" if setting.is_active else "deactivated"
    flash(f'Setting "{setting.display_name}" {status} successfully!', 'success')
    return redirect(url_for('main.settings'))

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

@main.route('/leads/<int:id>/detail', endpoint='lead_detail_full')
@login_required
def lead_detail(id):
    lead = Lead.query.get_or_404(id)
    interactions = LeadInteraction.query.filter_by(lead_id=id).order_by(desc(LeadInteraction.interaction_date)).all()
    quotes = LeadQuote.query.filter_by(lead_id=id).order_by(desc(LeadQuote.created_at)).all()
    
    quote_form = LeadQuoteForm()
    quote_form.course_id.choices = [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    interaction_form = LeadInteractionForm()
    followup_form = LeadFollowupForm()
    
    return render_template('leads/detail.html',
                         lead=lead,
                         interactions=interactions,
                         quotes=quotes,
                         quote_form=quote_form,
                         interaction_form=interaction_form,
                         followup_form=followup_form)

@main.route("/leads/<int:id>/add_quote", methods=["POST"])
@login_required
def add_lead_quote(id):
    lead = Lead.query.get_or_404(id)
    
    # Get form data directly from request since we're using a simple form
    course_id = request.form.get('course_id', type=int)
    quoted_amount = request.form.get('quoted_amount', type=float)
    valid_until = request.form.get('valid_until')
    quote_notes = request.form.get('quote_notes', '')
    currency = request.form.get('currency', 'AED')
    
    if not course_id or not quoted_amount or not valid_until:
        flash("Please fill all required fields", "error")
        return redirect(url_for("main.lead_detail", lead_id=id))
    
    try:
        # Parse the date
        from datetime import datetime
        valid_until_date = datetime.strptime(valid_until, '%Y-%m-%d').date()
        
        quote = LeadQuote(
            lead_id=id,
            course_id=course_id,
            quoted_amount=quoted_amount,
            currency=currency,
            valid_until=valid_until_date,
            quote_notes=quote_notes,
            created_by_id=current_user.id
        )
        
        # Update lead status and quoted amount
        if lead.status not in ["Converted", "Lost"]:
            lead.status = "Quoted"
            lead.quoted_amount = quoted_amount
        
        db.session.add(quote)
        db.session.commit()
        flash("Quote added successfully!", "success")
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding quote: {str(e)}", "error")
    
    return redirect(url_for("main.lead_detail", lead_id=id))

@main.route("/leads/<int:lead_id>/add_activity", methods=["POST"])
@login_required
def add_lead_activity(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    form = ActivityForm()
    
    if form.validate_on_submit():
        # Add new interaction as activity comment
        interaction = LeadInteraction(
            lead_id=lead_id,
            interaction_type='Comment',
            interaction_date=datetime.now(),
            content=form.comment.data,
            created_by_id=current_user.id,
            is_important=False
        )
        
        db.session.add(interaction)
        db.session.commit()
        flash("Activity comment added successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error: {error}", "error")
    
    return redirect(url_for("main.lead_detail", lead_id=lead_id))

@main.route("/leads/<int:id>/add_interaction", methods=["POST"])
@login_required
def add_lead_interaction(id):
    lead = Lead.query.get_or_404(id)
    form = LeadInteractionForm()
    
    if form.validate_on_submit():
        interaction = LeadInteraction(
            lead_id=id,
            interaction_type=form.interaction_type.data,
            interaction_date=datetime.combine(form.interaction_date.data, datetime.min.time()),
            notes=form.notes.data,
            outcome=form.outcome.data,
            created_by_id=current_user.id
        )
        
        lead.last_contact_date = form.interaction_date.data
        
        db.session.add(interaction)
        db.session.commit()
        flash("Interaction recorded successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")
    
    return redirect(url_for("main.lead_detail", lead_id=id))



@main.route("/leads/<int:id>/update_followup", methods=["POST"])
@login_required
def update_lead_followup(id):
    lead = Lead.query.get_or_404(id)
    
    # ROLE-BASED ACCESS CONTROL
    if not (current_user.is_admin() or current_user.can_view_all_leads or lead.created_by_id == current_user.id):
        return jsonify({
            'success': False,
            'message': 'You can only edit your own leads!'
        }), 403

    form = LeadFollowupForm()
    
    if form.validate_on_submit():
        try:
            # Store old values for logging
            old_date = lead.next_followup_date
            old_time = lead.followup_time
            old_type = lead.followup_type
            old_priority = lead.followup_priority

            # Update lead with new values
            lead.next_followup_date = form.followup_date.data
            lead.followup_time = form.followup_time.data
            lead.followup_type = form.followup_type.data
            lead.followup_priority = form.priority.data

            # Log the change as an interaction
            content = f"Follow-up updated: "
            changes = []
            if old_date != form.followup_date.data:
                changes.append(f"Date changed from {old_date or 'Not set'} to {form.followup_date.data}")
            if old_time != form.followup_time.data:
                changes.append(f"Time changed from {old_time or 'Not set'} to {form.followup_time.data}")
            if old_type != form.followup_type.data:
                changes.append(f"Type changed from {old_type or 'Not set'} to {form.followup_type.data}")
            if old_priority != form.priority.data:
                changes.append(f"Priority changed from {old_priority or 'Not set'} to {form.priority.data}")
            if form.notes.data:
                changes.append(f"Notes: {form.notes.data}")
            
            content += "; ".join(changes) if changes else "No changes made"

            interaction = LeadInteraction(
                lead_id=lead.id,
                interaction_type='Follow-up Update',
                interaction_date=datetime.now(),
                content=content,
                created_by_id=current_user.id,
                is_important=True
            )
            
            db.session.add(interaction)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Follow-up updated successfully!'
            })
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating follow-up: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'Error updating follow-up: {str(e)}'
            }), 500
    else:
        errors = []
        for field, field_errors in form.errors.items():
            for error in field_errors:
                errors.append(f"{field}: {error}")
        return jsonify({
            'success': False,
            'message': 'Form validation failed',
            'errors': errors
        }), 400 

@main.route('/corporate-leads/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_corporate_lead(id):
    lead = CorporateTraining.query.get_or_404(id)
    form = CorporateTrainingForm(obj=lead)
    form.course_names.choices = [(str(c.id), c.name) for c in Course.query.filter_by(is_active=True).all()]
    
    if lead.course_names:
        try:
            form.course_names.data = json.loads(lead.course_names)
        except json.JSONDecodeError:
            form.course_names.data = []
    
    if form.validate_on_submit():
        form.populate_obj(lead)
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

@main.route("/trainers")
@login_required
def trainers():
    trainers = Trainer.query.filter_by(is_active=True).all()
    trainer_form = TrainerForm()
    
    return render_template("trainers.html", trainers=trainers, trainer_form=trainer_form)

@main.route("/trainers/add", methods=["POST"])
@login_required
def add_trainer():
    form = TrainerForm()
    
    if form.validate_on_submit():
        trainer = Trainer(
            name=form.name.data,
            phone=form.phone.data,
            email=form.email.data,
            specialization=form.specialization.data,
            is_active=form.is_active.data
        )
        
        db.session.add(trainer)
        db.session.flush()
        
        for course_id in form.course_ids.data:
            trainer_course = TrainerCourse(trainer_id=trainer.id, course_id=course_id)
            db.session.add(trainer_course)
        
        db.session.commit()
        flash("Trainer added successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")
    
    return redirect(url_for("main.trainers"))

@main.route("/trainers/<int:id>/schedule")
@login_required
def trainer_schedule(id):
    trainer = Trainer.query.get_or_404(id)
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    
    # Calculate list of days for the week
    week_days = [start_of_week + timedelta(days=i) for i in range(7)]
    
    current_week_classes = ClassSchedule.query.filter(
        ClassSchedule.trainer_id == id,
        ClassSchedule.class_date >= start_of_week,
        ClassSchedule.class_date <= end_of_week,
        ClassSchedule.is_cancelled == False
    ).order_by(ClassSchedule.class_date, ClassSchedule.start_time).all()
    
    # Generate time slots
    time_slots = []
    for hour in range(8, 22):
        for minute in [0, 30]:
            time_slots.append(f"{hour:02d}:{minute:02d}")
    
    # Group classes by date and time (for efficiency)
    schedule_grid = {}
    for day in week_days:
        schedule_grid[day] = {ts: [] for ts in time_slots}
    
    for class_item in current_week_classes:
        time_str = class_item.start_time.strftime('%H:%M')
        if time_str in schedule_grid[class_item.class_date]:
            schedule_grid[class_item.class_date][time_str].append(class_item)
    
    schedule_form = ClassScheduleForm()
    schedule_form.trainer_id.choices = [(trainer.id, trainer.name)]
    schedule_form.trainer_id.data = trainer.id
    schedule_form.course_id.choices = [(c.id, c.name) for c in trainer.courses]
    schedule_form.student_ids.choices = [(s.id, s.name) for s in Student.query.filter_by(status="Active").all()]
    
    if not current_week_classes:
        flash("No classes scheduled for this week.", "info")
    
    return render_template("trainer_schedule.html",
                          trainer=trainer,
                          schedule_grid=schedule_grid,
                          time_slots=time_slots,
                          current_week_classes=current_week_classes,
                          schedule_form=schedule_form,
                          start_of_week=start_of_week,
                          end_of_week=end_of_week,
                          week_days=week_days)

@main.route("/schedule/add_class", methods=["POST"])
@login_required
def add_class_schedule():
    form = ClassScheduleForm()
    form.trainer_id.choices = [(t.id, t.name) for t in Trainer.query.filter_by(is_active=True).all()]
    form.course_id.choices = [(c.id, c.name) for c in Course.query.filter_by(is_active=True).all()]
    form.student_ids.choices = [(s.id, s.name) for s in Student.query.filter_by(status="Active").all()]
    
    if form.validate_on_submit():
        class_schedule = ClassSchedule(
            trainer_id=form.trainer_id.data,
            course_id=form.course_id.data,
            class_date=form.class_date.data,
            start_time=form.start_time.data,
            duration_minutes=form.duration_minutes.data,
            class_type=form.class_type.data,
            location=form.location.data,
            online_link=form.online_link.data,
            notes=form.notes.data
        )
        
        db.session.add(class_schedule)
        db.session.flush()
        
        for student_id in form.student_ids.data:
            class_student = ClassStudent(
                class_schedule_id=class_schedule.id,
                student_id=student_id
            )
            db.session.add(class_student)
        
        db.session.commit()
        flash("Class scheduled successfully!", "success")
        return redirect(url_for("main.trainer_schedule", id=form.trainer_id.data))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")
        return redirect(url_for("main.trainers"))

# ENHANCED STUDENT MANAGEMENT ROUTES

@main.route('/students/<int:id>/delete', methods=['POST'])
@login_required
def delete_student_record(id):
    if not current_user.is_admin():
        flash('Access denied. Only admins can delete students.', 'error')
        return redirect(url_for('main.students'))
    
    student = Student.query.get_or_404(id)
    try:
        db.session.delete(student)
        db.session.commit()
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting student: {str(e)}")
        flash('An error occurred while deleting the student. Please try again.', 'error')
    
    return redirect(url_for('main.students'))

@main.route('/students/<int:id>/overview')
@login_required
def student_overview(id):
    student = Student.query.get_or_404(id)
    return render_template('student_detail.html', student=student)

# ENHANCED TRAINER MANAGEMENT ROUTES
@main.route('/trainers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_trainer(id):
    if not current_user.is_admin():
        flash('Access denied. Only admins can edit trainers.', 'error')
        return redirect(url_for('main.trainers'))
    
    trainer = Trainer.query.get_or_404(id)
    form = TrainerForm(obj=trainer)
    
    if request.method == 'GET':
        return render_template('edit_trainer.html', form=form, trainer=trainer)
    
    if form.validate_on_submit():
        try:
            form.populate_obj(trainer)
            db.session.commit()
            flash('Trainer updated successfully!', 'success')
            return redirect(url_for('main.trainers'))
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating trainer: {str(e)}")
            flash('An error occurred while updating the trainer. Please try again.', 'error')
    
    return render_template('edit_trainer.html', form=form, trainer=trainer)

@main.route('/trainers/<int:id>/delete', methods=['POST'])
@login_required
def delete_trainer(id):
    if not current_user.is_admin():
        flash('Access denied. Only admins can delete trainers.', 'error')
        return redirect(url_for('main.trainers'))
    
    trainer = Trainer.query.get_or_404(id)
    try:
        db.session.delete(trainer)
        db.session.commit()
        flash('Trainer deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting trainer: {str(e)}")
        flash('An error occurred while deleting the trainer. Please try again.', 'error')
    
    return redirect(url_for('main.trainers'))

@main.route('/trainers/<int:id>')
@login_required
def trainer_detail(id):
    trainer = Trainer.query.get_or_404(id)
    
    # Get upcoming schedules
    from datetime import datetime
    upcoming_schedules = ClassSchedule.query.filter(
        ClassSchedule.trainer_id == id,
        ClassSchedule.class_date >= datetime.now().date(),
        ClassSchedule.is_cancelled == False
    ).order_by(ClassSchedule.class_date, ClassSchedule.start_time).limit(5).all()
    
    return render_template('trainer_detail.html', trainer=trainer, upcoming_schedules=upcoming_schedules)

@main.route("/schedule/weekly")
@login_required
def weekly_schedule():
    from datetime import datetime, timedelta
    
    week_offset = request.args.get("week", 0, type=int)
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    
    week_classes = ClassSchedule.query.filter(
        ClassSchedule.class_date >= start_of_week,
        ClassSchedule.class_date <= end_of_week,
        ClassSchedule.is_cancelled == False
    ).order_by(ClassSchedule.class_date, ClassSchedule.start_time).all()
    
    week_schedule = {}
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        week_schedule[day] = [cls for cls in week_classes if cls.class_date == day]
    
    return render_template("weekly_schedule.html",
                         week_schedule=week_schedule,
                         start_of_week=start_of_week,
                         end_of_week=end_of_week,
                         week_offset=week_offset)

@main.route("/schedule/monthly")
@login_required
def monthly_schedule():
    from datetime import datetime, timedelta
    from calendar import monthrange
    
    year = request.args.get("year", datetime.now().year, type=int)
    month = request.args.get("month", datetime.now().month, type=int)
    
    first_day = datetime(year, month, 1).date()
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num).date()
    
    month_classes = ClassSchedule.query.filter(
        ClassSchedule.class_date >= first_day,
        ClassSchedule.class_date <= last_day,
        ClassSchedule.is_cancelled == False
    ).order_by(ClassSchedule.class_date, ClassSchedule.start_time).all()
    
    monthly_schedule = {}
    current_day = first_day
    while current_day <= last_day:
        monthly_schedule[current_day] = [cls for cls in month_classes if cls.class_date == current_day]
        current_day += timedelta(days=1)
    
    return render_template("monthly_schedule.html",
                         monthly_schedule=monthly_schedule,
                         year=year,
                         month=month,
                         first_day=first_day,
                         last_day=last_day)

@main.route("/payments")
@login_required
def payments():
    vault_provider = PaymentProvider.query.filter_by(name="Vault").first()
    tabby_provider = PaymentProvider.query.filter_by(name="Tabby").first()
    tamara_provider = PaymentProvider.query.filter_by(name="Tamara").first()
    
    vault_links = PaymentLink.query.filter_by(provider_id=vault_provider.id).order_by(desc(PaymentLink.created_at)).all() if vault_provider else []
    tabby_links = PaymentLink.query.filter_by(provider_id=tabby_provider.id).order_by(desc(PaymentLink.created_at)).all() if tabby_provider else []
    tamara_links = PaymentLink.query.filter_by(provider_id=tamara_provider.id).order_by(desc(PaymentLink.created_at)).all() if tamara_provider else []
    
    total_pending = PaymentLink.query.filter_by(status="pending").count()
    total_paid = PaymentLink.query.filter_by(status="paid").count()
    total_failed = PaymentLink.query.filter_by(status="failed").count()
    
    payment_link_form = PaymentLinkForm()
    payment_link_form.lead_id.choices = [(0, "Select Lead")] + [(l.id, l.name) for l in Lead.query.all()]
    payment_link_form.student_id.choices = [(0, "Select Student")] + [(s.id, s.name) for s in Student.query.all()]
    payment_link_form.provider_id.choices = [(p.id, p.name) for p in PaymentProvider.query.filter_by(is_active=True).all()]
    
    return render_template("payments.html",
                         vault_provider=vault_provider,
                         tabby_provider=tabby_provider,
                         tamara_provider=tamara_provider,
                         vault_links=vault_links,
                         tabby_links=tabby_links,
                         tamara_links=tamara_links,
                         total_pending=total_pending,
                         total_paid=total_paid,
                         total_failed=total_failed,
                         payment_link_form=payment_link_form)

@main.route("/payments/create_link", methods=["POST"])
@login_required
def create_payment_link():
    form = PaymentLinkForm()
    form.lead_id.choices = [(0, "Select Lead")] + [(l.id, l.name) for l in Lead.query.all()]
    form.student_id.choices = [(0, "Select Student")] + [(s.id, s.name) for s in Student.query.all()]
    form.provider_id.choices = [(p.id, p.name) for p in PaymentProvider.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        try:
            import uuid
            payment_reference = f"PAY_{uuid.uuid4().hex[:8].upper()}"
            
            from datetime import timedelta
            expires_at = datetime.now() + timedelta(days=form.expires_in_days.data)
            
            payment_link = PaymentLink(
                lead_id=form.lead_id.data if form.lead_id.data > 0 else None,
                student_id=form.student_id.data if form.student_id.data > 0 else None,
                provider_id=form.provider_id.data,
                amount=form.amount.data,
                currency=form.currency.data,
                description=form.description.data,
                payment_reference=payment_reference,
                expires_at=expires_at,
                created_by_id=current_user.id
            )
            
            provider = PaymentProvider.query.get(form.provider_id.data)
            
            customer_info = None
            if form.lead_id.data and form.lead_id.data > 0:
                lead = Lead.query.get(form.lead_id.data)
                if lead:
                    customer_info = {
                        "name": lead.name,
                        "email": lead.email or "",
                        "phone": lead.phone or ""
                    }
            
            callback_url = url_for('main.payment_callback', _external=True)
            api_result = create_payment_link(
                provider=provider.name.lower(),
                amount=form.amount.data,
                currency=form.currency.data,
                description=form.description.data,
                customer_info=customer_info,
                callback_url=callback_url
            )
            
            if api_result.get('success'):
                payment_link.payment_url = api_result.get('payment_link')
                payment_link.external_payment_id = api_result.get('payment_id')
            else:
                payment_link.payment_url = f"#{provider.name.lower()}_payment_pending"
            
            db.session.add(payment_link)
            db.session.commit()
            
            flash(f"Payment link created successfully! Reference: {payment_reference}", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating payment link: {str(e)}", "error")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")
    
    return redirect(url_for("main.payments"))

@main.route("/payments/providers")
@login_required
def payment_providers():
    providers = PaymentProvider.query.all()
    provider_form = PaymentProviderForm()
    
    return render_template("payment_providers.html", 
                         providers=providers, 
                         provider_form=provider_form)

@main.route("/payments/providers/add", methods=["POST"])
@login_required
def add_payment_provider():
    form = PaymentProviderForm()
    
    if form.validate_on_submit():
        try:
            existing_provider = PaymentProvider.query.filter_by(name=form.name.data).first()
            
            if existing_provider:
                existing_provider.api_key = form.api_key.data
                existing_provider.api_secret = form.api_secret.data
                existing_provider.environment = form.environment.data
                existing_provider.webhook_url = form.webhook_url.data
                existing_provider.is_active = form.is_active.data
                flash(f"{form.name.data} provider updated successfully!", "success")
            else:
                provider = PaymentProvider(
                    name=form.name.data,
                    api_key=form.api_key.data,
                    api_secret=form.api_secret.data,
                    environment=form.environment.data,
                    webhook_url=form.webhook_url.data,
                    is_active=form.is_active.data
                )
                db.session.add(provider)
                flash(f"{form.name.data} provider added successfully!", "success")
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving provider: {str(e)}", "error")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")
    
    return redirect(url_for("main.payment_providers"))

@main.route("/payments/settings")
@login_required
def payment_settings():
    settings = PaymentSettings.query.first()
    form = PaymentSettingsForm()
    
    if settings:
        form.company_name.data = settings.company_name
        form.company_email.data = settings.company_email
        form.company_phone.data = settings.company_phone
        form.company_address.data = settings.company_address
        form.tax_registration_number.data = settings.tax_registration_number
        form.payment_terms.data = settings.payment_terms
        form.invoice_notes.data = settings.invoice_notes
        form.default_currency.data = settings.default_currency
        form.auto_send_receipts.data = settings.auto_send_receipts
        form.payment_reminder_enabled.data = settings.payment_reminder_enabled
        form.payment_reminder_days.data = settings.payment_reminder_days
    
    return render_template("payment_settings.html", form=form, settings=settings)

@main.route("/payments/settings/save", methods=["POST"])
@login_required
def save_payment_settings():
    form = PaymentSettingsForm()
    
    if form.validate_on_submit():
        try:
            settings = PaymentSettings.query.first()
            
            if not settings:
                settings = PaymentSettings()
                db.session.add(settings)
            
            settings.company_name = form.company_name.data
            settings.company_email = form.company_email.data
            settings.company_phone = form.company_phone.data
            settings.company_address = form.company_address.data
            settings.tax_registration_number = form.tax_registration_number.data
            settings.payment_terms = form.payment_terms.data
            settings.invoice_notes = form.invoice_notes.data
            settings.default_currency = form.default_currency.data
            settings.auto_send_receipts = form.auto_send_receipts.data
            settings.payment_reminder_enabled = form.payment_reminder_enabled.data
            settings.payment_reminder_days = form.payment_reminder_days.data
            settings.updated_at = datetime.now()
            
            db.session.commit()
            flash("Payment settings saved successfully!", "success")
            
        except Exception as e:
            db.session.rollback()
            flash(f"Error saving settings: {str(e)}", "error")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "error")
    
    return redirect(url_for("main.payment_settings"))

def generate_vault_payment_url(payment_link, provider):
    return f"https://vault-api-{provider.environment}.com/pay/{payment_link.payment_reference}"

def generate_tabby_payment_url(payment_link, provider):
    return f"https://api.tabby.ai/{provider.environment}/checkout/{payment_link.payment_reference}"

def generate_tamara_payment_url(payment_link, provider):
    return f"https://api.tamara.co/{provider.environment}/checkout/{payment_link.payment_reference}"

# User Management Routes
@main.route('/users')
@login_required
def users():
    """View all users - only for admins and users with user management permission"""
    if not (current_user.is_admin() or current_user.can_manage_users):
        flash('Access denied. You do not have permission to manage users.', 'error')
        return redirect(url_for('main.dashboard'))
    
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=all_users)

@main.route('/users/add', methods=['GET', 'POST'])
@login_required  
def add_user():
    """Add new user - only for admins"""
    if not current_user.is_admin():
        flash('Access denied. Only administrators can add users.', 'error')
        return redirect(url_for('main.dashboard'))
    
    form = UserForm()
    
    if form.validate_on_submit():
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists!', 'error')
            return render_template('add_user.html', form=form)
        
        # Create new user
        new_user = User()
        new_user.username = form.username.data
        new_user.email = form.email.data
        new_user.password_hash = generate_password_hash(form.password.data)
        new_user.role = form.role.data
        new_user.active = form.active.data
        new_user.created_by_id = current_user.id
        
        # Set permissions for superadmin role
        if form.role.data == 'superadmin':
            new_user.can_view_all_leads = form.can_view_all_leads.data
            new_user.can_manage_users = form.can_manage_users.data
            new_user.can_view_reports = form.can_view_reports.data
            new_user.can_manage_courses = form.can_manage_courses.data
            new_user.can_manage_settings = form.can_manage_settings.data
        elif form.role.data == 'admin':
            # Admin gets all permissions
            new_user.can_view_all_leads = True
            new_user.can_manage_users = True
            new_user.can_view_reports = True
            new_user.can_manage_courses = True
            new_user.can_manage_settings = True
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User {new_user.username} created successfully!', 'success')
        return redirect(url_for('main.users'))
    
    return render_template('add_user.html', form=form)

@main.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    """Edit existing user - only for admins"""
    if not current_user.is_admin():
        flash('Access denied. Only administrators can edit users.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(id)
    form = EditUserForm(obj=user)
    
    if form.validate_on_submit():
        # Check if username or email conflicts with other users
        existing_user = User.query.filter(
            User.id != id,
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        
        if existing_user:
            flash('Username or email already exists!', 'error')
            return render_template('edit_user.html', form=form, user=user)
        
        # Update user details
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        user.active = form.active.data
        
        # Update permissions for superadmin role
        if form.role.data == 'superadmin':
            user.can_view_all_leads = form.can_view_all_leads.data
            user.can_manage_users = form.can_manage_users.data
            user.can_view_reports = form.can_view_reports.data
            user.can_manage_courses = form.can_manage_courses.data
            user.can_manage_settings = form.can_manage_settings.data
        elif form.role.data == 'admin':
            # Admin gets all permissions
            user.can_view_all_leads = True
            user.can_manage_users = True
            user.can_view_reports = True
            user.can_manage_courses = True
            user.can_manage_settings = True
        else:  # consultant
            user.can_view_all_leads = False
            user.can_manage_users = False
            user.can_view_reports = False
            user.can_manage_courses = False
            user.can_manage_settings = False
        
        db.session.commit()
        flash(f'User {user.username} updated successfully!', 'success')
        return redirect(url_for('main.users'))
    
    return render_template('edit_user.html', form=form, user=user)

@main.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(id):
    """Toggle user active/inactive status - only for admins"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(id)
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot deactivate your own account'}), 400
    
    user.active = not user.active
    db.session.commit()
    
    status = 'activated' if user.active else 'deactivated'
    return jsonify({'success': True, 'message': f'User {status} successfully'})

@main.route('/users/<int:id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(id):
    """Reset user password - only for admins"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(id)
    
    # Generate temporary password
    temp_password = f"temp{user.id}{datetime.now().strftime('%d%m')}"
    user.password_hash = generate_password_hash(temp_password)
    
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'message': f'Password reset successfully',
        'temp_password': temp_password
    })

@main.route('/profile')
@login_required
def user_profile():
    """View current user profile"""
    return render_template('user_profile.html', user=current_user)

@main.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change current user password"""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        if not check_password_hash(current_user.password_hash, form.current_password.data):
            flash('Current password is incorrect!', 'error')
            return render_template('change_password.html', form=form)
        
        if form.new_password.data != form.confirm_password.data:
            flash('New passwords do not match!', 'error')
            return render_template('change_password.html', form=form)
        
        current_user.password_hash = generate_password_hash(form.new_password.data)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('main.user_profile'))
    
    return render_template('change_password.html', form=form)