import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, request, jsonify, current_app
import jwt
from werkzeug.security import check_password_hash
from models import db, Staff, Child, Appointment, Vaccination, Vaccine, Provider, Notification
from functools import wraps
from datetime import datetime, timedelta

staff_bp = Blueprint('staff', __name__, url_prefix='/api/staff')

def _generate_token(payload, expires_sec=3600):
    payload['exp'] = datetime.utcnow() + timedelta(seconds=expires_sec)
    return jwt.encode(payload, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithm='HS256')

def _verify_token(token, max_age=3600):
    try:
        data = jwt.decode(token, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithms=['HS256'])
        return data
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def staff_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization') or request.headers.get('X-Staff-Token')
        if not auth:
            return jsonify({'error': 'Missing token'}), 401

        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1]
        else:
            token = auth

        data = _verify_token(token)
        if not data:
            return jsonify({'error': 'Invalid or expired token'}), 401

        return f(staff_id=data.get('id'), *args, **kwargs)

    return wrapper


@staff_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    staff = Staff.query.filter_by(email=email).first()
    if staff and check_password_hash(staff.password_hash, password):
        # Check if staff is approved
        if staff.status != 'approved':
            return jsonify({'error': 'Account not approved yet. Please wait for admin approval.'}), 403
        
        payload = {'id': staff.id, 'email': email, 'role': staff.role}
        token = _generate_token(payload)
        return jsonify({'token': token, 'user': staff.to_dict()}), 200

    return jsonify({'error': 'Invalid credentials'}), 401


@staff_bp.route('/dashboard', methods=['GET'])
@staff_required
def dashboard(staff_id):
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff not found'}), 404

    # Get overview counts
    children_count = Child.query.count()
    appointments_count = Appointment.query.count()
    vaccinations_count = Vaccination.query.count()
    providers_count = Provider.query.count()

    # Get recent appointments
    recent_appointments = Appointment.query.order_by(Appointment.scheduled_date.desc()).limit(10).all()

    dashboard_data = {
        'staff': staff.to_dict(),
        'children_count': children_count,
        'appointments_count': appointments_count,
        'vaccinations_count': vaccinations_count,
        'providers_count': providers_count,
        'recent_appointments': [a.to_dict() for a in recent_appointments]
    }

    return jsonify(dashboard_data), 200


@staff_bp.route('/children', methods=['GET'])
@staff_required
def list_children(staff_id):
    children = Child.query.all()
    return jsonify({'children': [c.to_dict() for c in children]}), 200


@staff_bp.route('/appointments', methods=['GET'])
@staff_required
def list_appointments(staff_id):
    appointments = Appointment.query.all()
    return jsonify({'appointments': [a.to_dict() for a in appointments]}), 200


@staff_bp.route('/child/<int:child_id>', methods=['GET'])
@staff_required
def get_child(staff_id, child_id):
    child = Child.query.get(child_id)
    if not child:
        return jsonify({'error': 'Child not found'}), 404

    vaccinations = Vaccination.query.filter_by(child_id=child_id).all()
    appointments = Appointment.query.filter_by(child_id=child_id).all()

    return jsonify({
        'child': child.to_dict(),
        'vaccinations': [v.to_dict() for v in vaccinations],
        'appointments': [a.to_dict() for a in appointments]
    }), 200


@staff_bp.route('/appointment/<int:appointment_id>', methods=['PUT'])
@staff_required
def update_appointment(staff_id, appointment_id):
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404

    data = request.get_json() or {}
    if 'status' in data:
        appointment.status = data.get('status')
    if 'notes' in data:
        appointment.notes = data.get('notes')

    try:
        db.session.commit()
        return jsonify({'appointment': appointment.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@staff_bp.route('/vaccination/<int:vaccination_id>', methods=['PUT'])
@staff_required
def update_vaccination(staff_id, vaccination_id):
    vaccination = Vaccination.query.get(vaccination_id)
    if not vaccination:
        return jsonify({'error': 'Vaccination not found'}), 404

    data = request.get_json() or {}
    if 'status' in data:
        vaccination.status = data.get('status')
    if 'notes' in data:
        vaccination.notes = data.get('notes')
    if 'vaccination_date' in data:
        try:
            from datetime import datetime as _dt
            vaccination.vaccination_date = _dt.fromisoformat(data['vaccination_date']).date()
        except (ValueError, TypeError):
            pass

    # ── Sync VaccinationSchedule when marked as completed ───────────────────
    # The certificate reads VaccinationSchedule, so both tables must agree.
    if data.get('status') == 'completed':
        from models import VaccinationSchedule
        from datetime import date as _date
        completion_date = vaccination.vaccination_date or _date.today()
        matching_schedule = VaccinationSchedule.query.filter_by(
            child_id=vaccination.child_id,
            vaccine_id=vaccination.vaccine_id
        ).first()
        if matching_schedule:
            matching_schedule.status = 'completed'
            matching_schedule.completed_date = completion_date

    try:
        db.session.commit()
        return jsonify({'vaccination': vaccination.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@staff_bp.route('/appointment/<int:appointment_id>/cancel', methods=['POST'])
@staff_required
def cancel_appointment(staff_id, appointment_id):
    """Cancel an appointment with a reason (staff only)"""
    appointment = Appointment.query.get(appointment_id)
    if not appointment:
        return jsonify({'error': 'Appointment not found'}), 404

    data = request.get_json() or {}
    
    try:
        cancellation_reason = data.get('reason', 'Cancelled by healthcare staff')
        appointment.status = 'cancelled'
        appointment.cancellation_reason = cancellation_reason
        
        db.session.commit()
        
        # Create notification about cancellation
        if appointment.child:
            notification = Notification(
                child_id=appointment.child_id,
                notification_type='appointment_cancelled',
                title='Appointment Cancelled',
                message=f'The appointment scheduled for {appointment.scheduled_date.strftime("%Y-%m-%d")} has been cancelled. Reason: {cancellation_reason}',
                is_read=False
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify({
            'message': 'Appointment cancelled successfully',
            'appointment': appointment.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
