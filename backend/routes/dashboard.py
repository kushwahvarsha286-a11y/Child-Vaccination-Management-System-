"""
Dashboard Routes
Provides analytics, statistics, and overview endpoints for all user roles
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, request, jsonify, current_app
import jwt
from datetime import datetime, date, timedelta
from models import db, User, Staff, Child, Vaccination, VaccinationSchedule, Appointment, Notification, Vaccine, Provider
from sqlalchemy import func, and_

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')


def verify_token(token):
    """Verify JWT token"""
    try:
        data = jwt.decode(token, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithms=['HS256'])
        return data
    except:
        return None


def get_auth_user():
    """Extract and verify user from Authorization header"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return None, None
    
    token = auth.split(' ', 1)[1]
    data = verify_token(token)
    if not data:
        return None, None
    
    return data, data.get('role')


# ============= PARENT DASHBOARD =============

@dashboard_bp.route('/parent', methods=['GET'])
def parent_dashboard():
    """Parent dashboard with vaccination overview"""
    data, role = get_auth_user()
    if not data or role != 'parent':
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = data.get('user_id')
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get all children for this parent
    children = Child.query.filter_by(parent_email=user.email).all()
    
    # Get all vaccination schedules for these children in one query
    child_ids = [c.id for c in children]
    if child_ids:
        all_schedules = VaccinationSchedule.query.filter(VaccinationSchedule.child_id.in_(child_ids)).all()
        schedules_by_child = {}
        for sched in all_schedules:
            if sched.child_id not in schedules_by_child:
                schedules_by_child[sched.child_id] = []
            schedules_by_child[sched.child_id].append(sched)
    else:
        schedules_by_child = {}
    
    dashboard_data = {
        'user': user.to_dict(),
        'total_children': len(children),
        'children': [],
        'overall_stats': {
            'total_vaccinations': 0,
            'completed_vaccinations': 0,
            'pending_vaccinations': 0,
            'overdue_vaccinations': 0,
            'upcoming_vaccinations_count': 0
        }
    }
    
    today = date.today()
    
    for child in children:
        child_schedules = schedules_by_child.get(child.id, [])
        completed = len([s for s in child_schedules if s.status == 'completed'])
        pending = len([s for s in child_schedules if s.status == 'pending'])
        overdue = len([s for s in child_schedules if s.status == 'pending' and s.scheduled_date < today])
        upcoming = len([s for s in child_schedules if s.status == 'pending' and s.scheduled_date >= today])
        
        child_dict = child.to_dict()
        child_dict['vaccination_stats'] = {
            'total': len(child_schedules),
            'completed': completed,
            'pending': pending,
            'overdue': overdue,
            'upcoming': upcoming,
            'progress_percentage': round((completed / len(child_schedules) * 100) if child_schedules else 0, 2)
        }
        
        # Get next upcoming vaccination
        next_vac = next((s for s in child_schedules if s.status == 'pending' and s.scheduled_date >= today), None)
        if next_vac:
            next_vac = min([s for s in child_schedules if s.status == 'pending' and s.scheduled_date >= today], key=lambda x: x.scheduled_date)
            child_dict['next_vaccination'] = next_vac.to_dict()
        
        dashboard_data['children'].append(child_dict)
        
        # Update overall stats
        dashboard_data['overall_stats']['total_vaccinations'] += len(child_schedules)
        dashboard_data['overall_stats']['completed_vaccinations'] += completed
        dashboard_data['overall_stats']['pending_vaccinations'] += pending
        dashboard_data['overall_stats']['overdue_vaccinations'] += overdue
        dashboard_data['overall_stats']['upcoming_vaccinations_count'] += upcoming
    
    return jsonify(dashboard_data), 200


# ============= STAFF/DOCTOR DASHBOARD =============

@dashboard_bp.route('/staff', methods=['GET'])
def staff_dashboard():
    """Staff/Doctor dashboard with child and vaccination management"""
    data, role = get_auth_user()
    if not data or role not in ['staff', 'doctor', 'admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    staff_id = data.get('user_id')
    staff = Staff.query.get(staff_id)
    if not staff and role != 'admin':
        return jsonify({'error': 'Staff not found'}), 404
    
    today = date.today()
    
    # Get all children (staff can see all)
    children = Child.query.all()
    
    dashboard_data = {
        'staff': staff.to_dict() if staff else {'first_name': 'Admin', 'last_name': '', 'role': 'admin'},
        'stats': {
            'total_children': len(children),
            'total_vaccinations_completed': 0,
            'total_vaccinations_pending': 0,
            'missed_vaccinations': 0,
            'appointment_count': 0
        },
        'today_schedule': [],
        'overdue_vaccinations': []
    }
    
    # Count statistics
    all_schedules = VaccinationSchedule.query.all()
    dashboard_data['stats']['total_vaccinations_completed'] = len([s for s in all_schedules if s.status == 'completed'])
    dashboard_data['stats']['total_vaccinations_pending'] = len([s for s in all_schedules if s.status == 'pending'])
    dashboard_data['stats']['missed_vaccinations'] = len([s for s in all_schedules if s.status == 'delayed'])
    
    # Get today's appointments
    today_appointments = Appointment.query.filter(
        Appointment.scheduled_date >= datetime.combine(today, datetime.min.time()),
        Appointment.scheduled_date <= datetime.combine(today, datetime.max.time())
    ).all()
    
    dashboard_data['stats']['appointment_count'] = len(today_appointments)
    for apt in today_appointments[:10]:  # Limit to 10
        dashboard_data['today_schedule'].append(apt.to_dict())
    
    # Get overdue vaccinations
    overdue_schedules = VaccinationSchedule.query.filter(
        VaccinationSchedule.status == 'pending',
        VaccinationSchedule.scheduled_date < today
    ).all()
    
    for schedule in overdue_schedules[:20]:  # Limit to 20
        vac_dict = schedule.to_dict()
        vac_dict['child_name'] = schedule.child.name if schedule.child else None
        vac_dict['child_id'] = schedule.child_id
        dashboard_data['overdue_vaccinations'].append(vac_dict)
    
    return jsonify(dashboard_data), 200


# ============= ADMIN DASHBOARD =============

@dashboard_bp.route('/admin', methods=['GET'])
def admin_dashboard():
    """Admin dashboard with system-wide analytics"""
    data, role = get_auth_user()
    if not data or role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    today = date.today()
    
    dashboard_data = {
        'system_stats': {
            'total_parents': User.query.filter_by(role='parent').count(),
            'total_children': Child.query.count(),
            'total_staff': Staff.query.count(),
            'total_vaccinations_completed': 0,
            'total_vaccinations_pending': 0,
            'total_appointments': Appointment.query.count(),
        },
        'vaccination_analytics': {},
        'recent_registrations': [],
        'stock_alerts': [],
        'system_notifications': []
    }
    
    # Count vaccination statistics
    all_schedules = VaccinationSchedule.query.all()
    dashboard_data['system_stats']['total_vaccinations_completed'] = len([s for s in all_schedules if s.status == 'completed'])
    dashboard_data['system_stats']['total_vaccinations_pending'] = len([s for s in all_schedules if s.status == 'pending'])
    
    # Get vaccine distribution analytics
    from sqlalchemy import func, desc
    vaccine_stats = db.session.query(
        Vaccine.name,
        func.count(VaccinationSchedule.id).label('total'),
        func.sum(db.case((VaccinationSchedule.status == 'completed', 1), else_=0)).label('completed')
    ).join(VaccinationSchedule).group_by(Vaccine.name).all()
    
    for stat in vaccine_stats:
        dashboard_data['vaccination_analytics'][stat[0]] = {
            'total': stat[1],
            'completed': stat[2] or 0,
            'pending': stat[1] - (stat[2] or 0)
        }
    
    # Get recent registrations (last 7 days)
    seven_days_ago = today - timedelta(days=7)
    recent_children = Child.query.filter(
        Child.created_at >= seven_days_ago
    ).order_by(Child.created_at.desc()).limit(10).all()
    
    dashboard_data['recent_registrations'] = [c.to_dict() for c in recent_children]
    
    return jsonify(dashboard_data), 200


# ============= COMMON ENDPOINTS =============

@dashboard_bp.route('/child/<int:child_id>', methods=['GET'])
def child_overview(child_id):
    """Get comprehensive overview for a specific child.
    Parents may only view their own children.
    """
    data, role = get_auth_user()
    if not data:
        return jsonify({'error': 'Unauthorized'}), 401

    child = Child.query.get(child_id)
    if not child:
        return jsonify({'error': 'Child not found'}), 404

    # Enforce parent ownership
    if role == 'parent':
        user = User.query.get(data.get('user_id'))
        if not user or child.parent_email != user.email:
            return jsonify({'error': 'Access denied'}), 403

    # Get all schedules
    schedules = VaccinationSchedule.query.filter_by(child_id=child_id).all()

    overview = {
        'child': child.to_dict(),
        'vaccination_schedule': [s.to_dict() for s in schedules],
        'vaccination_summary': {
            'total': len(schedules),
            'completed': len([s for s in schedules if s.status == 'completed']),
            'pending': len([s for s in schedules if s.status == 'pending']),
            'delayed': len([s for s in schedules if s.status == 'delayed'])
        }
    }

    return jsonify(overview), 200


@dashboard_bp.route('/stats', methods=['GET'])
def get_dashboard_stats():
    """Get quick stats for dashboard (role-aware)."""
    try:
        data, role = get_auth_user()
        if data and role == 'parent':
            user = User.query.get(data.get('user_id'))
            if user:
                parent_child_ids = [
                    c.id for c in Child.query.filter_by(parent_email=user.email).all()
                ]
                vax_count = Vaccination.query.filter(
                    Vaccination.child_id.in_(parent_child_ids)
                ).count() if parent_child_ids else 0
                apt_count = Appointment.query.filter(
                    Appointment.child_id.in_(parent_child_ids)
                ).count() if parent_child_ids else 0
                unread_count = Notification.query.filter(
                    Notification.child_id.in_(parent_child_ids),
                    Notification.is_read == False
                ).count() if parent_child_ids else 0
                stats = {
                    'children': len(parent_child_ids),
                    'vaccinations': vax_count,
                    'appointments': apt_count,
                    'providers': Provider.query.count(),
                    'unread_notifications': unread_count,
                    'scheduled_appointments': apt_count,
                    'pending_vaccinations': 0
                }
                return jsonify(stats), 200
        # Staff / Admin — full system stats
        stats = {
            'children': Child.query.count(),
            'vaccinations': Vaccination.query.count(),
            'appointments': Appointment.query.count(),
            'providers': Provider.query.count(),
            'unread_notifications': Notification.query.filter_by(is_read=False).count(),
            'scheduled_appointments': Appointment.query.filter_by(status='scheduled').count(),
            'pending_vaccinations': VaccinationSchedule.query.filter_by(status='pending').count()
        }
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@dashboard_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get detailed statistics for analytics"""
    data, role = get_auth_user()
    if not data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = {
        'role': role,
        'timestamp': datetime.now().isoformat()
    }
    
    if role == 'parent':
        user = User.query.get(data.get('user_id'))
        children = Child.query.filter_by(parent_email=user.email).all()
        
        stats['children_count'] = len(children)
        stats['vaccinations'] = {
            'total': sum(len(VaccinationSchedule.query.filter_by(child_id=c.id).all()) for c in children),
            'completed': sum(len([s for s in VaccinationSchedule.query.filter_by(child_id=c.id).all() if s.status == 'completed']) for c in children),
            'pending': sum(len([s for s in VaccinationSchedule.query.filter_by(child_id=c.id).all() if s.status == 'pending']) for c in children)
        }
    
    elif role in ['staff', 'doctor']:
        stats['children_managed'] = Child.query.count()
        stats['appointments_handled'] = Appointment.query.count()
        stats['vaccinations_administered'] = len([v for v in Vaccination.query.all() if v.status == 'completed'])
    
    elif role == 'admin':
        from models import Vaccine
        stats['total_users'] = {
            'parents': User.query.filter_by(role='parent').count(),
            'staff': Staff.query.count(),
            'admins': User.query.filter_by(role='admin').count()
        }
        stats['total_children'] = Child.query.count()
        stats['vaccines_in_database'] = Vaccine.query.count()
    
    return jsonify(stats), 200
