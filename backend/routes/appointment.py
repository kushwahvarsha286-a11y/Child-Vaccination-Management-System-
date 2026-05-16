from flask import Blueprint, request, jsonify
from models import db, Appointment, Child, Provider, Vaccine, Notification
from datetime import datetime
import jwt
from flask import current_app
from functools import wraps

CITY_HOSPITAL_NAME = 'City Hospital'

def get_city_hospital_id():
    """Return the ID of City Hospital (the single provider)."""
    hospital = Provider.query.filter_by(name=CITY_HOSPITAL_NAME).first()
    if not hospital:
        hospital = Provider.query.first()  # fallback: use any provider
    return hospital.id if hospital else None

appointment_bp = Blueprint('appointment', __name__, url_prefix='/api/appointments')

def get_auth_user():
    """Extract and verify user from Authorization header"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return None, None
    
    token = auth.split(' ', 1)[1]
    try:
        data = jwt.decode(token, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithms=['HS256'])
        return data, data.get('role')
    except:
        return None, None

@appointment_bp.route('/', methods=['GET'])
def get_all_appointments():
    """Get appointments – filtered by role.
    Parents only see their own children's appointments.
    Staff and admin see all appointments.
    """
    auth_data, role = get_auth_user()

    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        # Get IDs of children belonging to this parent
        parent_child_ids = [
            c.id for c in Child.query.filter_by(parent_email=user.email).all()
        ]
        if not parent_child_ids:
            return jsonify([]), 200
        appointments = Appointment.query.filter(
            Appointment.child_id.in_(parent_child_ids)
        ).all()
    else:
        # Staff / admin – full access
        appointments = Appointment.query.all()

    return jsonify([a.to_dict() for a in appointments])

@appointment_bp.route('/child/<int:child_id>', methods=['GET'])
def get_child_appointments(child_id):
    """Get appointments for a specific child"""
    appointments = Appointment.query.filter_by(child_id=child_id).all()
    return jsonify([a.to_dict() for a in appointments])

@appointment_bp.route('/<int:appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """Get a specific appointment – parents may only access their own."""
    appointment = Appointment.query.get_or_404(appointment_id)
    auth_data, role = get_auth_user()
    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        child = Child.query.get(appointment.child_id)
        if not child or child.parent_email != user.email:
            return jsonify({'error': 'Access denied'}), 403
    return jsonify(appointment.to_dict())

@appointment_bp.route('/', methods=['POST'])
def create_appointment():
    """Create a new appointment – always linked to City Hospital."""
    data = request.get_json()
    
    # If parent is creating, verify they own the child
    auth_data, role = get_auth_user()
    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        child = Child.query.get(data.get('child_id'))
        if not child or child.parent_email != user.email:
            return jsonify({'error': 'You can only schedule appointments for your own children'}), 403
    
    try:
        # Some frontend frameworks send ISO format with 'Z' which datetime.fromisoformat doesn't like in <3.11 without replace
        date_str = data['scheduled_date'].replace('Z', '+00:00')
        scheduled_date = datetime.fromisoformat(date_str)
        
        if scheduled_date.date() < datetime.now().date():
            return jsonify({'error': 'Cannot schedule appointment in the past'}), 400
        
        # Always use City Hospital as the provider
        city_hospital_id = get_city_hospital_id()
        if not city_hospital_id:
            return jsonify({'error': 'City Hospital not found in database. Please contact administrator.'}), 500
            
        appointment = Appointment(
            child_id=data['child_id'],
            provider_id=city_hospital_id,  # Always City Hospital
            scheduled_date=scheduled_date,
            vaccine_id=data.get('vaccine_id'),
            status=data.get('status', 'scheduled'),
            notes=data.get('notes')
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        # Create notification
        child = Child.query.get(data['child_id'])
        if child:
            notification = Notification(
                child_id=child.id,
                notification_type='appointment_reminder',
                title='Appointment Scheduled',
                message=f'An appointment has been scheduled for {child.name} at City Hospital',
                is_read=False
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify(appointment.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@appointment_bp.route('/<int:appointment_id>', methods=['PUT'])
def update_appointment(appointment_id):
    """Update an appointment – parents may only update their own."""
    appointment = Appointment.query.get_or_404(appointment_id)
    auth_data, role = get_auth_user()
    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        child = Child.query.get(appointment.child_id)
        if not child or child.parent_email != user.email:
            return jsonify({'error': 'Access denied'}), 403
    data = request.get_json()
    
    try:
        if 'scheduled_date' in data:
            date_str = data['scheduled_date'].replace('Z', '+00:00')
            new_date = datetime.fromisoformat(date_str)
            if new_date.date() < datetime.now().date():
                return jsonify({'error': 'Cannot schedule appointment in the past'}), 400
            appointment.scheduled_date = new_date
        if 'status' in data:
            appointment.status = data['status']
        if 'notes' in data:
            appointment.notes = data['notes']
        if 'vaccine_id' in data:
            appointment.vaccine_id = data['vaccine_id']
        
        db.session.commit()
        return jsonify(appointment.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@appointment_bp.route('/<int:appointment_id>', methods=['DELETE'])
def delete_appointment(appointment_id):
    """Delete an appointment – parents may only delete their own."""
    appointment = Appointment.query.get_or_404(appointment_id)
    auth_data, role = get_auth_user()
    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        child = Child.query.get(appointment.child_id)
        if not child or child.parent_email != user.email:
            return jsonify({'error': 'Access denied'}), 403
    
    try:
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'message': 'Appointment deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@appointment_bp.route('/<int:appointment_id>/cancel', methods=['POST'])
def cancel_appointment(appointment_id):
    """Cancel an appointment with a reason"""
    appointment = Appointment.query.get_or_404(appointment_id)
    data = request.get_json() or {}
    
    try:
        cancellation_reason = data.get('reason', 'No reason provided')
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
        return jsonify({'error': str(e)}), 400
