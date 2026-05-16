from flask import Blueprint, request, jsonify, send_file, current_app
from models import db, Child, Vaccination, VaccinationSchedule, Vaccine, Notification, Provider
from datetime import datetime
from services.pdf_generator import generate_vaccination_certificate
import jwt

vaccination_bp = Blueprint('vaccination', __name__, url_prefix='/api/vaccinations')


def get_city_hospital_id():
    """Return the ID of City Hospital (the single provider)."""
    hospital = Provider.query.filter_by(name='City Hospital').first()
    if not hospital:
        hospital = Provider.query.first()
    return hospital.id if hospital else None


def get_auth_user():
    """Extract and verify user from Authorization header"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        return None, None
    token = auth.split(' ', 1)[1]
    try:
        data = jwt.decode(token, current_app.config.get('SECRET_KEY', 'dev-secret'), algorithms=['HS256'])
        return data, data.get('role')
    except Exception:
        return None, None

@vaccination_bp.route('/certificate/<int:child_id>', methods=['GET'])
def download_certificate(child_id):
    """Generate and download vaccination certificate PDF with fully up-to-date data."""
    from models import User
    from datetime import date

    child = Child.query.get_or_404(child_id)

    # ── Resolve parent name from the logged-in user (JWT) ────────────────────
    auth_data, role = get_auth_user()
    certificate_parent_name = child.parent_name or 'N/A'  # safe default

    if auth_data:
        if role == 'parent':
            user = User.query.get(auth_data.get('user_id'))
            if user:
                certificate_parent_name = f"{user.first_name} {user.last_name}".strip()
        elif role in ['staff', 'doctor', 'admin']:
            # For staff-generated certs, look up parent from User table by email
            parent_user = User.query.filter_by(email=child.parent_email).first()
            if parent_user:
                certificate_parent_name = f"{parent_user.first_name} {parent_user.last_name}".strip()

    # ── Build the most up-to-date vaccination list ───────────────────────────
    # VaccinationSchedule holds the standard schedule (pending/completed status
    # set via the schedule update workflow).
    # Vaccination holds records created/updated directly by staff.
    # We merge both so nothing is missed.
    today = date.today()
    schedules = VaccinationSchedule.query.filter_by(child_id=child_id).all()
    direct_vacs = Vaccination.query.filter_by(child_id=child_id).all()

    # Build a mapping of vaccine_id → completed VaccinationSchedule
    # so we can sync any direct Vaccination completion back into schedules.
    sched_by_vaccine = {s.vaccine_id: s for s in schedules}

    # For direct Vaccination records marked completed, ensure the matching
    # VaccinationSchedule is also marked completed (live, in-memory only —
    # no DB write here; we persist inside the PUT endpoints instead).
    for v in direct_vacs:
        if v.status == 'completed' and v.vaccine_id in sched_by_vaccine:
            sched = sched_by_vaccine[v.vaccine_id]
            if sched.status != 'completed':
                sched.status = 'completed'
                sched.completed_date = v.vaccination_date or today

    # Use schedules as the source of truth for the PDF
    # (the PDF generator filters to status == 'completed' internally)
    pdf_buffer = generate_vaccination_certificate(
        child,
        schedules,
        parent_name=certificate_parent_name
    )

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"{child.name.replace(' ', '_')}_vaccination_certificate.pdf",
        mimetype='application/pdf'
    )

@vaccination_bp.route('/', methods=['GET'])
def get_all_vaccinations():
    """Get vaccinations – filtered by role.
    Parents only see their own children's records.
    """
    auth_data, role = get_auth_user()
    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        parent_child_ids = [
            c.id for c in Child.query.filter_by(parent_email=user.email).all()
        ]
        if not parent_child_ids:
            return jsonify([]), 200
        vaccinations = Vaccination.query.filter(
            Vaccination.child_id.in_(parent_child_ids)
        ).all()
    else:
        vaccinations = Vaccination.query.all()
    return jsonify([v.to_dict() for v in vaccinations])

@vaccination_bp.route('/child/<int:child_id>', methods=['GET'])
def get_child_vaccinations(child_id):
    """Get vaccinations for a specific child – parents may only access their own."""
    auth_data, role = get_auth_user()
    if auth_data and role == 'parent':
        from models import User
        user = User.query.get(auth_data.get('user_id'))
        if not user:
            return jsonify({'error': 'User not found'}), 401
        child = Child.query.get(child_id)
        if not child or child.parent_email != user.email:
            return jsonify({'error': 'Access denied'}), 403
    vaccinations = Vaccination.query.filter_by(child_id=child_id).all()
    return jsonify([v.to_dict() for v in vaccinations])

@vaccination_bp.route('/<int:vaccination_id>', methods=['GET'])
def get_vaccination(vaccination_id):
    """Get a specific vaccination"""
    vaccination = Vaccination.query.get_or_404(vaccination_id)
    return jsonify(vaccination.to_dict())

@vaccination_bp.route('/', methods=['POST'])
def create_vaccination():
    """Create a new vaccination record – always linked to City Hospital."""
    data = request.get_json()
    
    try:
        vaccination = Vaccination(
            child_id=data['child_id'],
            vaccine_id=data['vaccine_id'],
            vaccination_date=datetime.fromisoformat(data['vaccination_date']).date(),
            provider_id=get_city_hospital_id(),  # Always City Hospital
            status=data.get('status', 'completed'),
            notes=data.get('notes')
        )
        
        db.session.add(vaccination)
        db.session.commit()
        
        return jsonify(vaccination.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@vaccination_bp.route('/<int:vaccination_id>', methods=['PUT'])
def update_vaccination(vaccination_id):
    """Update a vaccination record and keep VaccinationSchedule in sync."""
    vaccination = Vaccination.query.get_or_404(vaccination_id)
    data = request.get_json()
    from datetime import date as _date

    try:
        if 'vaccination_date' in data:
            vaccination.vaccination_date = datetime.fromisoformat(data['vaccination_date']).date()
        if 'status' in data:
            vaccination.status = data['status']
        if 'notes' in data:
            vaccination.notes = data['notes']
        if 'provider_id' in data:
            vaccination.provider_id = data['provider_id']

        # ── When a vaccination is marked completed, stamp the date and sync ──
        # the matching VaccinationSchedule row so the certificate is accurate.
        if data.get('status') == 'completed':
            completion_date = vaccination.vaccination_date or _date.today()
            # Sync to the schedule table
            matching_schedule = VaccinationSchedule.query.filter_by(
                child_id=vaccination.child_id,
                vaccine_id=vaccination.vaccine_id
            ).first()
            if matching_schedule:
                matching_schedule.status = 'completed'
                matching_schedule.completed_date = completion_date

        db.session.commit()
        return jsonify(vaccination.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@vaccination_bp.route('/<int:vaccination_id>', methods=['DELETE'])
def delete_vaccination(vaccination_id):
    """Delete a vaccination record"""
    vaccination = Vaccination.query.get_or_404(vaccination_id)
    
    try:
        db.session.delete(vaccination)
        db.session.commit()
        return jsonify({'message': 'Vaccination deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@vaccination_bp.route('/vaccines/', methods=['GET'])
def get_all_vaccines():
    """Get all available vaccines"""
    vaccines = Vaccine.query.all()
    return jsonify([v.to_dict() for v in vaccines])

@vaccination_bp.route('/vaccines/', methods=['POST'])
def create_vaccine():
    """Create a new vaccine type"""
    data = request.get_json()
    
    try:
        vaccine = Vaccine(
            name=data['name'],
            description=data.get('description'),
            recommended_age_months=data.get('recommended_age_months')
        )
        
        db.session.add(vaccine)
        db.session.commit()
        
        return jsonify(vaccine.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
