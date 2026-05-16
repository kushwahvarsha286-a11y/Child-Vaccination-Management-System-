import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, jsonify, request
from models import db, Child
from validators import ChildValidator, ValidationError
from datetime import datetime
import jwt
from flask import current_app

child_bp = Blueprint('child_bp', __name__, url_prefix='/api/children')

def verify_token():
    """Verify JWT token from Authorization header"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return None

    token = auth.split(' ', 1)[1]
    try:
        return jwt.decode(token, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_auth_user():
    """Extract authenticated user payload and role"""
    data = verify_token()
    if not data:
        return None, None
    return data, data.get('role')


@child_bp.route('', methods=['GET'])
def get_children():
    """Get all children with role-based filtering."""
    current_app.logger.info('Incoming /api/children request from %s', request.remote_addr)
    auth_data, role = get_auth_user()
    if not auth_data:
        current_app.logger.warning('Unauthorized /api/children access attempt from %s', request.remote_addr)
        return jsonify({'error': 'Unauthorized - valid Bearer token required'}), 401

    try:
        if role == 'admin':
            children = Child.query.all()

        elif role == 'parent':
            from models import User
            user = User.query.get(auth_data.get('user_id'))
            if not user:
                return jsonify({'error': 'Parent user not found'}), 401
            children = Child.query.filter_by(parent_email=user.email).all()

        elif role == 'staff':
            from models import Staff
            staff = Staff.query.get(auth_data.get('user_id'))
            if not staff:
                return jsonify({'error': 'Staff user not found'}), 401
            # If child assignment is configured, only return assigned children
            if hasattr(Child, 'assigned_staff_id'):
                children = Child.query.filter_by(assigned_staff_id=staff.id).all()
            else:
                children = Child.query.all()

        else:
            return jsonify({'error': 'Forbidden - invalid role'}), 403

        return jsonify([c.to_dict() for c in children]), 200

    except Exception as e:
        return jsonify({'error': 'Database error while retrieving children', 'details': str(e)}), 500

@child_bp.route('/<int:child_id>', methods=['GET'])
def get_child(child_id):
    """Get a specific child"""
    data, role = get_auth_user()
    if not data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    child = Child.query.get_or_404(child_id)
    
    # Parent can only access their own children
    if role == 'parent':
        user_email = data.get('email')
        if child.parent_email != user_email:
            return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(child.to_dict())

@child_bp.route('', methods=['POST'])
def create_child():

    """Create a new child with validation"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Verify parent can only create child for themselves
    auth_data, role = get_auth_user()
    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        # Parent can only create children with their own email as parent_email
        if data.get('parent_email') and data.get('parent_email') != user.email:
            return jsonify({'error': 'You can only create children for yourself'}), 403
        # Set parent_email to logged-in parent's email
        data['parent_email'] = user.email
        data['parent_name'] = f"{user.first_name} {user.last_name}"
    
    try:
        # Validate input data
        validated_data = ChildValidator.validate_child_data(data)
        
        # Create child object with validated data
        child = Child(
            name=validated_data['name'],
            date_of_birth=validated_data['date_of_birth'],
            gender=validated_data.get('gender'),
            parent_name=validated_data['parent_name'],
            parent_email=validated_data['parent_email'],
            parent_phone=validated_data.get('parent_phone'),
            relation=validated_data.get('relation')
        )
        
        db.session.add(child)
        db.session.flush()
        
        from services.schedule_generator import generate_vaccination_schedule
        generate_vaccination_schedule(child)
        
        db.session.commit()
        
        return jsonify(child.to_dict()), 201
    
    except ValidationError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@child_bp.route('/<int:child_id>', methods=['PUT'])
def update_child(child_id):
    """Update an existing child"""
    try:
        child = Child.query.get_or_404(child_id)
    except:
        return jsonify({'error': 'Child not found'}), 404
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        # Validate only the fields being updated
        if 'name' in data:
            from validators import Validator
            child.name = Validator.validate_name(data['name'], 'Child name')
        
        if 'gender' in data:
            from validators import Validator
            child.gender = Validator.validate_gender(data['gender'])
        
        if 'parent_name' in data:
            from validators import Validator
            child.parent_name = Validator.validate_name(data['parent_name'], 'Parent name')
        
        if 'parent_email' in data:
            from validators import Validator
            child.parent_email = Validator.validate_email(data['parent_email'])
        
        if 'parent_phone' in data:
            from validators import Validator
            child.parent_phone = Validator.validate_phone(data.get('parent_phone'))
        
        if 'relation' in data:
            from validators import Validator
            child.relation = Validator.validate_name(data['relation'], 'Relation')
        
        db.session.commit()
        return jsonify(child.to_dict())
    
    except ValidationError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500

@child_bp.route('/<int:child_id>', methods=['DELETE'])
def delete_child(child_id):
    """Delete a child"""
    try:
        child = Child.query.get_or_404(child_id)
    except:
        return jsonify({'error': 'Child not found'}), 404
    
    try:
        db.session.delete(child)
        db.session.commit()
        return jsonify({'message': 'Child deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500
