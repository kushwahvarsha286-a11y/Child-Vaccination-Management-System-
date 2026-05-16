import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, request, jsonify, current_app
import jwt
from werkzeug.security import check_password_hash
from models import db, User, Child, Appointment, Vaccination, Vaccine
from functools import wraps
from datetime import datetime, timedelta

parent_bp = Blueprint('parent', __name__, url_prefix='/api/parent')

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


def parent_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get('Authorization') or request.headers.get('X-Parent-Token')
        if not auth:
            return jsonify({'error': 'Missing token'}), 401

        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1]
        else:
            token = auth

        data = _verify_token(token)
        if not data:
            return jsonify({'error': 'Invalid or expired token'}), 401

        return f(parent_id=data.get('id'), *args, **kwargs)

    return wrapper


@parent_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Missing credentials'}), 400

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        payload = {'id': user.id, 'email': email, 'role': 'parent'}
        token = _generate_token(payload)
        return jsonify({'token': token, 'user': user.to_dict()}), 200

    return jsonify({'error': 'Invalid credentials'}), 401


@parent_bp.route('/dashboard', methods=['GET'])
@parent_required
def dashboard(parent_id):
    parent = User.query.get(parent_id)
    if not parent:
        return jsonify({'error': 'User not found'}), 404

    # Get all children for this parent (by email)
    children = Child.query.filter_by(parent_email=parent.email).all()
    child_ids = [c.id for c in children]

    # Get vaccinations and appointments for children
    vaccinations = []
    appointments = []
    if child_ids:
        vaccinations = Vaccination.query.filter(Vaccination.child_id.in_(child_ids)).all()
        appointments = Appointment.query.filter(Appointment.child_id.in_(child_ids)).all()

    dashboard_data = {
        'parent': parent.to_dict(),
        'children_count': len(children),
        'vaccinations_count': len(vaccinations),
        'appointments_count': len(appointments),
        'children': [c.to_dict() for c in children],
        'vaccinations': [v.to_dict() for v in vaccinations],
        'appointments': [a.to_dict() for a in appointments]
    }

    return jsonify(dashboard_data), 200


@parent_bp.route('/my-children', methods=['GET'])
@parent_required
def my_children(parent_id):
    parent = User.query.get(parent_id)
    if not parent:
        return jsonify({'error': 'User not found'}), 404

    children = Child.query.filter_by(parent_email=parent.email).all()
    return jsonify({'children': [c.to_dict() for c in children]}), 200


@parent_bp.route('/child/<int:child_id>/vaccinations', methods=['GET'])
@parent_required
def child_vaccinations(parent_id, child_id):
    child = Child.query.get(child_id)
    if not child:
        return jsonify({'error': 'Child not found'}), 404

    parent = User.query.get(parent_id)
    if child.parent_email != parent.email:
        return jsonify({'error': 'Unauthorized'}), 403

    vaccinations = Vaccination.query.filter_by(child_id=child_id).all()
    return jsonify({'vaccinations': [v.to_dict() for v in vaccinations]}), 200


@parent_bp.route('/child/<int:child_id>/appointments', methods=['GET'])
@parent_required
def child_appointments(parent_id, child_id):
    child = Child.query.get(child_id)
    if not child:
        return jsonify({'error': 'Child not found'}), 404

    parent = User.query.get(parent_id)
    if child.parent_email != parent.email:
        return jsonify({'error': 'Unauthorized'}), 403

    appointments = Appointment.query.filter_by(child_id=child_id).all()
    return jsonify({'appointments': [a.to_dict() for a in appointments]}), 200
