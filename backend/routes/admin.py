import sys
import os
import secrets
import string
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, request, jsonify, current_app
import jwt
from werkzeug.security import check_password_hash, generate_password_hash
from models import db, User, Staff, Child, Vaccine, Provider, Appointment, AuditLog, VaccinationSchedule, Vaccination
from datetime import datetime, timedelta
from functools import wraps

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

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


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization') or request.headers.get('X-Admin-Token')
        if not auth:
            return jsonify({'error': 'Missing admin token'}), 401

        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1]
        else:
            token = auth

        data = _verify_token(token)
        if not data:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Verify payload refers to an admin user/staff
        role = data.get('role')
        if role != 'admin':
            return jsonify({'error': 'Forbidden - Admin access required'}), 403

        # attach admin info to request context if needed
        return f(*args, **kwargs)

    return wrapper


def log_action(user_id, user_type, action, entity_type, entity_id=None, changes=None):
    """Log admin action for audit trail"""
    try:
        ip_address = request.remote_addr
        log_entry = AuditLog(
            user_id=user_id,
            user_type=user_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            ip_address=ip_address
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        print(f"Error logging action: {e}")


# ============= AUTHENTICATION =============

@admin_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    # Prefer Staff table for admin users
    staff = Staff.query.filter_by(email=email).first()
    if staff and staff.role == 'admin' and check_password_hash(staff.password_hash, password):
        payload = {'id': staff.id, 'model': 'staff', 'role': staff.role, 'email': staff.email}
        token = _generate_token(payload)
        log_action(staff.id, 'staff', 'LOGIN', 'admin_login')
        return jsonify({'token': token, 'user': staff.to_dict()}), 200

    # fallback to User table (in case admin stored in users)
    user = User.query.filter_by(email=email).first()
    if user and getattr(user, 'role', None) == 'admin' and check_password_hash(user.password_hash, password):
        payload = {'id': user.id, 'model': 'user', 'role': user.role, 'email': user.email}
        token = _generate_token(payload)
        log_action(user.id, 'user', 'LOGIN', 'admin_login')
        return jsonify({'token': token, 'user': user.to_dict()}), 200

    return jsonify({'error': 'Invalid credentials or not an admin'}), 401


# ============= DASHBOARD & SUMMARY =============

@admin_bp.route('/summary', methods=['GET'])
@admin_required
def summary():
    """Get system summary statistics"""
    counts = {
        'users': User.query.count(),
        'staff': Staff.query.count(),
        'children': Child.query.count(),
        'vaccines': Vaccine.query.count(),
        'providers': Provider.query.count(),
        'appointments': Appointment.query.count(),
        'total_vaccinations': VaccinationSchedule.query.count(),
        'completed_vaccinations': VaccinationSchedule.query.filter_by(status='completed').count(),
        'pending_vaccinations': VaccinationSchedule.query.filter_by(status='pending').count()
    }
    return jsonify({'summary': counts}), 200


# ============= USER MANAGEMENT =============

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users():
    """List all users and staff"""
    users = [u.to_dict() for u in User.query.all()]
    staff = [s.to_dict() for s in Staff.query.all()]
    return jsonify({'users': users, 'staff': staff}), 200


@admin_bp.route('/create-admin', methods=['POST'])
@admin_required
def create_admin():
    """Create a new admin user (Admin only)"""
    data = request.get_json() or {}
    
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')
    
    if not all([first_name, last_name, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    existing_staff = Staff.query.filter_by(email=email).first()
    if existing_user or existing_staff:
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create admin staff user
    pw_hash = generate_password_hash(password)
    admin = Staff(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=pw_hash,
        role='admin',
        workplace='System'
    )
    
    db.session.add(admin)
    db.session.commit()
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('id'), token_data.get('model'), 'CREATE_ADMIN', 'staff', admin.id, f'Created admin user {email}')
    
    return jsonify({
        'success': True,
        'message': f'Admin user {email} created successfully',
        'admin': admin.to_dict()
    }), 201


@admin_bp.route('/staff/<int:staff_id>/role', methods=['PUT'])
@admin_required
def update_staff_role(staff_id):
    """Update staff role"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff not found'}), 404
    
    data = request.get_json() or {}
    new_role = data.get('role')
    
    if new_role not in ['staff', 'doctor', 'admin']:
        return jsonify({'error': 'Invalid role'}), 400
    
    old_role = staff.role
    staff.role = new_role
    db.session.commit()
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('id'), token_data.get('model'), 'UPDATE_ROLE', 'staff', staff_id, f'Changed role from {old_role} to {new_role}')
    
    return jsonify({
        'success': True,
        'message': f'Staff role updated to {new_role}',
        'staff': staff.to_dict()
    }), 200


@admin_bp.route('/user/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete a user account"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.role == 'admin':
        return jsonify({'error': 'Cannot delete admin users'}), 403
    
    db.session.delete(user)
    db.session.commit()
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('id'), token_data.get('model'), 'DELETE_USER', 'user', user_id, f'Deleted user {user.email}')
    
    return jsonify({'success': True, 'message': 'User deleted'}), 200


@admin_bp.route('/user/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update a user account"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json() or {}
    if 'first_name' in data:
        user.first_name = data['first_name']
    if 'last_name' in data:
        user.last_name = data['last_name']
    if 'email' in data:
        # Check if email is taken
        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != user_id:
            return jsonify({'error': 'Email already in use'}), 409
        user.email = data['email']
    if 'phone' in data:
        user.phone = data['phone']
    if 'address' in data:
        user.address = data['address']
    
    db.session.commit()
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('id'), token_data.get('model'), 'UPDATE_USER', 'user', user_id, f'Updated user {user.email}')
    
    return jsonify({'success': True, 'user': user.to_dict()}), 200


# ============= AUDIT LOGS =============

# Removed duplicate route; using the paginated version below


# ============= STAFF MANAGEMENT =============

@admin_bp.route('/staff', methods=['GET'])
@admin_required
def list_staff():
    """List all staff members"""
    staff_list = Staff.query.all()
    return jsonify({
        'total': len(staff_list),
        'staff': [s.to_dict() for s in staff_list]
    }), 200


@admin_bp.route('/staff', methods=['POST'])
@admin_required
def create_staff():
    """Admin-only: create a new staff account (always assigned to City Hospital)"""
    data = request.get_json() or {}
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone', '')
    specialty = data.get('specialty', '')

    if not all([first_name, last_name, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    if User.query.filter_by(email=email).first() or Staff.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    pw_hash = generate_password_hash(password)
    staff = Staff(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=pw_hash,
        role='staff',
        workplace='City Hospital',  # Always City Hospital
        phone=phone,
        specialty=specialty
    )
    try:
        db.session.add(staff)
        db.session.commit()

        # Audit log
        auth = request.headers.get('Authorization')
        if auth and auth.startswith('Bearer '):
            token_data = _verify_token(auth.split(' ', 1)[1])
            if token_data:
                log_action(token_data.get('user_id'), 'staff', 'CREATE_STAFF', 'staff', staff.id, f'Created staff {email}')

        return jsonify({'success': True, 'staff': staff.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/staff/<int:staff_id>', methods=['GET'])
@admin_required
def get_staff(staff_id):
    """Get staff details"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff not found'}), 404
    
    return jsonify(staff.to_dict()), 200


@admin_bp.route('/staff/<int:staff_id>', methods=['DELETE'])
@admin_required
def delete_staff(staff_id):
    """Delete staff member"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff not found'}), 404
    
    if staff.role == 'admin':
        return jsonify({'error': 'Cannot delete admin staff'}), 403
    
    db.session.delete(staff)
    db.session.commit()
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('user_id'), 'admin', 'DELETE_STAFF', 'staff', staff_id, f'Deleted staff member {staff.email}')
    
    return jsonify({'success': True, 'message': 'Staff member deleted'}), 200


# ============= AUDIT LOG & MONITORING =============

@admin_bp.route('/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    """Get system audit logs"""
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()
    total = AuditLog.query.count()
    
    return jsonify({
        'total': total,
        'limit': limit,
        'offset': offset,
        'logs': [l.to_dict() for l in logs]
    }), 200


@admin_bp.route('/audit-logs/<int:user_id>', methods=['GET'])
@admin_required
def get_user_audit_logs(user_id):
    """Get audit logs for a specific user"""
    logs = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.created_at.desc()).limit(50).all()
    
    return jsonify({
        'user_id': user_id,
        'total': len(logs),
        'logs': [l.to_dict() for l in logs]
    }), 200


# ============= CHILDREN & VACCINATION MANAGEMENT =============

@admin_bp.route('/children', methods=['GET'])
@admin_required
def get_all_children():
    """Get all registered children"""
    children = Child.query.all()
    
    children_data = []
    for child in children:
        child_dict = child.to_dict()
        schedules = VaccinationSchedule.query.filter_by(child_id=child.id).all()
        child_dict['vaccination_count'] = len(schedules)
        child_dict['completed_count'] = len([s for s in schedules if s.status == 'completed'])
        children_data.append(child_dict)
    
    return jsonify({
        'total': len(children),
        'children': children_data
    }), 200


@admin_bp.route('/children/<int:child_id>', methods=['DELETE'])
@admin_required
def delete_child(child_id):
    """Delete a child record"""
    child = Child.query.get(child_id)
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    db.session.delete(child)
    db.session.commit()
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('user_id'), 'admin', 'DELETE_CHILD', 'child', child_id, f'Deleted child {child.name}')
    
    return jsonify({'success': True, 'message': 'Child record deleted'}), 200


# ============= STAFF APPROVAL WORKFLOW =============

@admin_bp.route('/staff/pending', methods=['GET'])
@admin_required
def get_pending_staff():
    """Get all pending staff registrations for approval"""
    pending_staff = Staff.query.filter_by(status='pending').all()
    
    return jsonify({
        'total': len(pending_staff),
        'pending_staff': [s.to_dict() for s in pending_staff]
    }), 200


def generate_staff_id():
    """Generate unique staff ID: STAF-2026-001"""
    year = datetime.now().year
    # Find the highest existing staff_id for this year
    existing = Staff.query.filter(Staff.staff_id.like(f'STAF-{year}-%')).all()
    if existing:
        numbers = [int(s.staff_id.split('-')[-1]) for s in existing if s.staff_id]
        next_num = max(numbers) + 1 if numbers else 1
    else:
        next_num = 1
    return f'STAF-{year}-{next_num:03d}'


def generate_temp_password():
    """Generate secure temporary password (12 characters)"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(12))


@admin_bp.route('/staff/<int:staff_id>/approve', methods=['POST'])
@admin_required
def approve_staff(staff_id):
    """Approve pending staff registration and generate credentials"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff not found'}), 404
    
    if staff.status != 'pending':
        return jsonify({'error': 'Staff is not pending approval'}), 400
    
    # Generate staff ID
    staff.staff_id = generate_staff_id()
    
    # Only generate new password if this is admin-created staff (no existing password)
    # For public registrations, keep their original password
    temp_pass = None
    if not staff.password_hash:  # Admin-created staff
        temp_pass = generate_temp_password()
        staff.password_hash = generate_password_hash(temp_pass)
        staff.temp_password = generate_password_hash(temp_pass)
    
    staff.status = 'approved'
    
    db.session.commit()
    
    # Send approval email notification
    from services.mailer import send_staff_approval_notification
    staff_name = f"{staff.first_name} {staff.last_name}"
    send_staff_approval_notification(staff.email, staff_name, staff.staff_id, temp_pass or staff.password_hash)
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('user_id'), 'admin', 'APPROVE_STAFF', 'staff', staff_id, f'Approved staff {staff.email}')
    
    response_data = {
        'success': True,
        'message': 'Staff approved successfully and notification sent',
        'staff': staff.to_dict()
    }
    
    # Only include credentials if we generated a new password
    if temp_pass:
        response_data['credentials'] = {
            'staff_id': staff.staff_id,
            'temp_password': temp_pass
        }
    
    return jsonify(response_data), 200


@admin_bp.route('/staff/<int:staff_id>/reject', methods=['POST'])
@admin_required
def reject_staff(staff_id):
    """Reject pending staff registration"""
    staff = Staff.query.get(staff_id)
    if not staff:
        return jsonify({'error': 'Staff not found'}), 404
    
    if staff.status != 'pending':
        return jsonify({'error': 'Staff is not pending approval'}), 400
    
    data = request.get_json() or {}
    reason = data.get('reason', 'No reason provided')
    
    staff.status = 'rejected'
    db.session.commit()
    
    # Send rejection email notification
    from services.mailer import send_staff_rejection_notification
    staff_name = f"{staff.first_name} {staff.last_name}"
    send_staff_rejection_notification(staff.email, staff_name, reason)
    
    # Log action
    auth = request.headers.get('Authorization')
    if auth and auth.startswith('Bearer '):
        token_data = _verify_token(auth.split(' ', 1)[1])
        if token_data:
            log_action(token_data.get('user_id'), 'admin', 'REJECT_STAFF', 'staff', staff_id, f'Rejected staff {staff.email}: {reason}')
    
    return jsonify({
        'success': True,
        'message': 'Staff rejected successfully and notification sent',
        'reason': reason
    }), 200


# ============= SYSTEM HEALTH =============

@admin_bp.route('/health', methods=['GET'])
@admin_required
def system_health():
    """Check system health and stats"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected',
        'version': '2.0'
    }), 200

