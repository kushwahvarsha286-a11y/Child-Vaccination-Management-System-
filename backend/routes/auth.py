import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, request, jsonify, current_app
from models import db, User, Child, Staff
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import jwt

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

def generate_token(user_id, email, role, expires_in=3600):
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'exp': datetime.utcnow() + timedelta(seconds=expires_in)
    }
    return jwt.encode(payload, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithm='HS256')


def _verify_token(token):
    try:
        return jwt.decode(token, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithms=['HS256'])
    except Exception:
        return None


def admin_required(f):
    """Decorator: require admin JWT token"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization') or request.headers.get('X-Admin-Token')
        if not auth:
            return jsonify({'error': 'Admin token required'}), 401
        token = auth.split(' ', 1)[1] if auth.startswith('Bearer ') else auth
        data = _verify_token(token)
        if not data or data.get('role') != 'admin':
            return jsonify({'error': 'Forbidden – Admin access required'}), 403
        return f(*args, **kwargs)
    return wrapper


# ============= PARENT SIGNUP (Public) =============

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Public signup – Parents only"""
    data = request.get_json() or {}
    first_name = data.get('first_name') or data.get('firstName')
    last_name = data.get('last_name') or data.get('lastName')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')
    address = data.get('address')
    role = data.get('role') or 'parent'

    if role in ('admin', 'staff'):
        return jsonify({'error': 'Only parent accounts can be created here'}), 403

    if not first_name or not last_name or not email or not password:
        return jsonify({'error': 'Missing required fields'}), 400

    child_payload = data.get('child') or {}
    if not child_payload or not child_payload.get('name') or not child_payload.get('date_of_birth') or not child_payload.get('gender'):
        return jsonify({'error': 'Child name, gender, and date of birth are mandatory'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    pw_hash = generate_password_hash(password)
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=pw_hash,
        role='parent',
        phone=phone,
        address=address
    )

    try:
        db.session.add(user)
        db.session.flush()

        child_name = child_payload.get('name')
        child_dob = child_payload.get('date_of_birth')
        child_gender = child_payload.get('gender')
        relation = child_payload.get('relation')

        try:
            dob_obj = datetime.strptime(child_dob, '%Y-%m-%d').date()
        except Exception:
            dob_obj = None

        child = Child(
            name=child_name,
            date_of_birth=dob_obj,
            gender=child_gender,
            parent_name=f"{first_name} {last_name}",
            parent_email=email,
            parent_phone=phone,
            relation=relation
        )
        db.session.add(child)
        db.session.flush()

        from services.schedule_generator import generate_vaccination_schedule
        generate_vaccination_schedule(child)

        db.session.commit()
        return jsonify({'user': user.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============= STAFF CREATION (Admin Only) =============

@auth_bp.route('/signup/staff', methods=['POST'])
@admin_required
def signup_staff():
    """Admin-only: create a new staff account"""
    data = request.get_json() or {}
    first_name = data.get('first_name') or data.get('firstName')
    last_name = data.get('last_name') or data.get('lastName')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')
    specialty = data.get('specialty')

    if not first_name or not last_name or not email or not password:
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
        return jsonify({'staff': staff.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============= STAFF SELF-REGISTRATION (Public) =============

@auth_bp.route('/register/staff', methods=['POST'])
def register_staff():
    """Public staff registration - creates pending account for admin approval.
    All staff are automatically assigned to City Hospital.
    """
    data = request.get_json() or {}
    first_name = data.get('first_name') or data.get('firstName')
    last_name = data.get('last_name') or data.get('lastName')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')
    specialty = data.get('specialty')

    if not first_name or not last_name or not email or not password:
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
        specialty=specialty,
        status='pending'  # Pending admin approval
    )

    try:
        db.session.add(staff)
        db.session.commit()
        return jsonify({
            'message': 'Staff registration submitted successfully. Please wait for admin approval.',
            'staff': {
                'first_name': staff.first_name,
                'last_name': staff.last_name,
                'email': staff.email,
                'status': staff.status
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============= LOGIN =============

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Unified login endpoint for all three roles: parent, staff, admin
    Checks User table first (parents), then Staff table (staff + admin)
    """
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Check User table (parents)
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        token = generate_token(user.id, user.email, user.role)
        return jsonify({
            'token': token,
            'user': {
                'id': user.id,
                'name': f"{user.first_name} {user.last_name}".strip(),
                'email': user.email,
                'role': user.role
            }
        }), 200

    # Check Staff table (staff + admin)
    staff = Staff.query.filter_by(email=email).first()
    if staff and check_password_hash(staff.password_hash, password):
        # Check approval status
        if staff.status == 'pending':
            return jsonify({'error': 'Your account is pending admin approval. Please wait for the administrator to review your registration.'}), 403
        elif staff.status == 'rejected':
            return jsonify({'error': 'Your account registration has been rejected. Please contact the administrator for more information.'}), 403
        elif staff.status != 'approved':
            return jsonify({'error': 'Account not approved. Please wait for admin approval.'}), 403
        
        token = generate_token(staff.id, staff.email, staff.role)
        return jsonify({
            'token': token,
            'user': {
                'id': staff.id,
                'name': f"{staff.first_name} {staff.last_name}".strip(),
                'email': staff.email,
                'role': staff.role
            }
        }), 200

    return jsonify({'error': 'Invalid email or password'}), 401


# ============= PROFILE =============

@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get the logged-in user profile"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    data = _verify_token(auth.split(' ', 1)[1])
    if not data:
        return jsonify({'error': 'Invalid token'}), 401

    role = data.get('role')
    user_id = data.get('user_id')

    if role == 'parent':
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        children = Child.query.filter_by(parent_email=user.email).all()
        return jsonify({
            'user': user.to_dict(),
            'children': [c.to_dict() for c in children]
        }), 200
    else:
        staff = Staff.query.get(user_id)
        if not staff:
            return jsonify({'error': 'Staff not found'}), 404
        return jsonify({'user': staff.to_dict()}), 200


@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    """Update logged-in parent profile"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401
    token_data = _verify_token(auth.split(' ', 1)[1])
    if not token_data or token_data.get('role') != 'parent':
        return jsonify({'error': 'Unauthorized – Parents only'}), 403

    user = User.query.get(token_data.get('user_id'))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    body = request.get_json() or {}
    if 'first_name' in body:
        user.first_name = body['first_name']
    if 'last_name' in body:
        user.last_name = body['last_name']
    if 'phone' in body:
        user.phone = body['phone']
    if 'address' in body:
        user.address = body['address']

    try:
        db.session.commit()
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
