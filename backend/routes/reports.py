"""
Reports and Certificate Routes
Handles PDF generation, certificate downloads, and report management
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Blueprint, request, jsonify, current_app, send_file
import jwt
from datetime import datetime, date, timedelta
from models import db, User, Staff, Child, Vaccination, VaccinationSchedule, Report, Appointment
from services.pdf_generator import generate_vaccination_certificate
from services.qr_generator import generate_certificate_qr, generate_verification_code
import os
from pathlib import Path

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

# Directory for storing PDF certificates
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports_storage')
os.makedirs(REPORTS_DIR, exist_ok=True)


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


# ============= REPORT GENERATION =============

@reports_bp.route('/generate/child/<int:child_id>', methods=['POST'])
def generate_report(child_id):
    """Generate vaccination certificate for a child"""
    auth_data, role = get_auth_user()
    if not auth_data or role not in ['admin', 'staff', 'doctor', 'parent']:
        return jsonify({'error': 'Unauthorized'}), 401

    child = Child.query.get(child_id)
    if not child:
        return jsonify({'error': 'Child not found'}), 404

    # ── Resolve the REAL parent name from the logged-in User record ──────────
    # This is completely independent of child.parent_name.
    certificate_parent_name = None   # will be set below

    if role == 'parent':
        user = User.query.get(auth_data.get('user_id'))
        if not user or child.parent_email != user.email:
            return jsonify({'error': 'Unauthorized - not your child'}), 403
        # Real parent name: first_name + last_name from the User table
        certificate_parent_name = f"{user.first_name} {user.last_name}".strip()

    elif role in ['staff', 'doctor']:
        staff = Staff.query.get(auth_data.get('user_id'))
        certificate_parent_name = child.parent_name  # keep stored value for staff-generated certs
        if staff:
            # Staff generates on behalf; label accordingly
            certificate_parent_name = child.parent_name or "N/A"

    elif role == 'admin':
        certificate_parent_name = child.parent_name or "N/A"

    # ── Vaccination records: use BOTH tables for maximum accuracy ────────────
    # VaccinationSchedule holds the per-child schedule populated at registration.
    # Vaccination holds individual records created/updated by staff.
    # We merge them so the PDF reflects whichever table has the latest status.
    from models import VaccinationSchedule
    from datetime import date as _today_date
    today = _today_date.today()

    schedules = VaccinationSchedule.query.filter_by(child_id=child_id).all()
    direct_vacs = Vaccination.query.filter_by(child_id=child_id).all()

    # Build a quick lookup: vaccine_id -> schedule row
    sched_by_vaccine = {s.vaccine_id: s for s in schedules}

    # For any Vaccination row marked completed that doesn't yet reflect in the
    # schedule, update the in-memory schedule object so the PDF is accurate.
    for v in direct_vacs:
        if v.status == 'completed' and v.vaccine_id in sched_by_vaccine:
            sched = sched_by_vaccine[v.vaccine_id]
            if sched.status != 'completed':
                sched.status = 'completed'
                sched.completed_date = v.vaccination_date or today

    if not schedules and not direct_vacs:
        return jsonify({'error': 'No vaccination records found for this child'}), 404

    # Use schedules as the source of truth for the PDF
    # (the PDF generator filters to status == 'completed' internally)
    certificate_vaccinations = schedules if schedules else direct_vacs


    # ── Generate PDF with explicit, separate parent_name ─────────────────────
    pdf_buffer = generate_vaccination_certificate(
        child,
        certificate_vaccinations,
        parent_name=certificate_parent_name
    )
    
    # Generate QR code and verification
    qr_base64, qr_data = generate_certificate_qr(child_id, 0, child.name)
    verification_code = generate_verification_code(child_id)
    
    # Save PDF to disk
    pdf_filename = f"vaccination_certificate_{child_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    
    with open(pdf_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())
    
    # Create Report record
    staff_name = None
    staff_id = None
    if role in ['staff', 'doctor']:
        staff = Staff.query.get(auth_data.get('user_id'))
        if staff:
            staff_name = f"{staff.first_name} {staff.last_name}"
            staff_id = staff.id
    elif role == 'admin':
        staff_name = "System Administrator"
    else:
        user = User.query.get(auth_data.get('user_id'))
        if user:
            staff_name = f"{user.first_name} {user.last_name}"
    
    report = Report(
        child_id=child_id,
        report_type='vaccination_certificate',
        title=f'Vaccination Certificate - {child.name}',
        pdf_path=pdf_filename,
        qr_code=qr_base64,
        generated_by=staff_name,
        staff_id=staff_id,
        signature=verification_code,
        is_valid=True
    )
    
    db.session.add(report)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'report': report.to_dict(),
        'report_id': report.id,
        'message': 'Vaccination certificate generated successfully'
    }), 201



# ============= REPORT RETRIEVAL =============

@reports_bp.route('/<int:report_id>', methods=['GET'])
def get_report(report_id):
    """Get report details"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    # Check authorization
    data, role = get_auth_user()
    if data and role == 'parent':
        user = User.query.get(data.get('user_id'))
        child = Child.query.get(report.child_id)
        if child.parent_email != user.email:
            return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(report.to_dict()), 200


@reports_bp.route('/child/<int:child_id>', methods=['GET'])
def get_child_reports(child_id):
    """Get all reports for a child"""
    child = Child.query.get(child_id)
    if not child:
        return jsonify({'error': 'Child not found'}), 404
    
    # Check authorization
    data, role = get_auth_user()
    if not data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if role == 'parent':
        user = User.query.get(data.get('user_id'))
        if child.parent_email != user.email:
            return jsonify({'error': 'Unauthorized'}), 403
    
    reports = Report.query.filter_by(child_id=child_id, is_valid=True).order_by(Report.created_at.desc()).all()
    
    return jsonify({
        'child': child.to_dict(),
        'reports': [r.to_dict() for r in reports]
    }), 200


# ============= PDF DOWNLOAD =============

@reports_bp.route('/download/<int:report_id>', methods=['GET'])
def download_report(report_id):
    """Download PDF certificate"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    # Check authorization
    data, role = get_auth_user()
    if data and role == 'parent':
        user = User.query.get(data.get('user_id'))
        child = Child.query.get(report.child_id)
        if child.parent_email != user.email:
            return jsonify({'error': 'Unauthorized'}), 403
    
    pdf_path = os.path.join(REPORTS_DIR, report.pdf_path)
    if not os.path.exists(pdf_path):
        return jsonify({'error': 'PDF file not found'}), 404
    
    return send_file(
        pdf_path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=report.title.replace(' ', '_') + '.pdf'
    )


# ============= REPORT LISTING =============

@reports_bp.route('/', methods=['GET'])
def list_reports():
    """List reports (filtered by role)"""
    data, role = get_auth_user()
    if not data:
        return jsonify({'error': 'Unauthorized'}), 401
    
    if role == 'parent':
        # Get parent's children
        user = User.query.get(data.get('user_id'))
        children = Child.query.filter_by(parent_email=user.email).all()
        child_ids = [c.id for c in children]
        reports = Report.query.filter(Report.child_id.in_(child_ids)).order_by(Report.created_at.desc()).all()
    
    elif role in ['staff', 'doctor']:
        # Get reports generated by this staff
        staff = Staff.query.get(data.get('user_id'))
        reports = Report.query.filter_by(staff_id=staff.id).order_by(Report.created_at.desc()).all()
    
    elif role == 'admin':
        # Get all reports
        reports = Report.query.order_by(Report.created_at.desc()).all()
    
    else:
        return jsonify({'error': 'Invalid role'}), 403
    
    return jsonify({
        'total': len(reports),
        'reports': [r.to_dict() for r in reports]
    }), 200


# ============= REPORT VERIFICATION =============

@reports_bp.route('/verify/<int:report_id>', methods=['GET'])
def verify_report(report_id):
    """Verify certificate authenticity"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    if not report.is_valid:
        return jsonify({'error': 'Certificate is invalid or revoked'}), 400
    
    child = Child.query.get(report.child_id)
    if not child:
        return jsonify({'error': 'Associated child record not found'}), 404
    
    # Get vaccination status
    vaccinations = VaccinationSchedule.query.filter_by(child_id=report.child_id).all()
    completed_count = sum(1 for v in vaccinations if v.status == 'completed')
    total_count = len(vaccinations)
    
    return jsonify({
        'verified': True,
        'report_id': report.id,
        'child_name': child.name,
        'child_dob': child.date_of_birth.isoformat() if child.date_of_birth else None,
        'generated_at': report.created_at.isoformat(),
        'generated_by': report.generated_by,
        'vaccination_summary': {
            'total_scheduled': total_count,
            'completed': completed_count,
            'pending': total_count - completed_count
        },
        'qr_data': report.qr_code,
        'verification_code': report.signature
    }), 200

@reports_bp.route('/verify/<int:report_id>', methods=['POST'])
def verify_report_with_code(report_id):
    """Verify a report using QR code or verification code"""
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    data = request.get_json() or {}
    verification_code = data.get('verification_code')
    
    is_valid = report.is_valid and (report.signature == verification_code if verification_code else True)
    
    return jsonify({
        'report_id': report_id,
        'is_valid': is_valid,
        'child_name': report.child.name if report.child else None,
        'generated_date': report.created_at.isoformat(),
        'generated_by': report.generated_by,
        'verification_code': report.signature if is_valid else None
    }), 200


# ============= REPORT DELETION (Admin Only) =============

@reports_bp.route('/<int:report_id>', methods=['DELETE'])
def delete_report(report_id):
    """Delete a report (soft delete by marking invalid)"""
    data, role = get_auth_user()
    if not data or role != 'admin':
        return jsonify({'error': 'Unauthorized - Admin only'}), 403
    
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    # Soft delete
    report.is_valid = False
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Report deleted'}), 200


# ============= APPOINTMENT REPORTS =============

@reports_bp.route('/appointments', methods=['POST'])
def generate_appointment_report():
    """Generate appointment report for a date range"""
    data, role = get_auth_user()
    if not data or role not in ['admin', 'staff']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    req_data = request.get_json() or {}
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    child_id = req_data.get('child_id')  # Optional: filter by child
    
    if not start_date or not end_date:
        return jsonify({'error': 'Start date and end date are required'}), 400
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Query appointments
    query = Appointment.query.filter(
        Appointment.scheduled_date >= start,
        Appointment.scheduled_date <= end
    )
    
    if child_id:
        query = query.filter_by(child_id=child_id)
    
    appointments = query.order_by(Appointment.scheduled_date).all()
    
    # Generate PDF
    from services.pdf_generator import generate_appointment_report_pdf
    pdf_buffer = generate_appointment_report_pdf(appointments, start, end, child_id)
    
    # Save PDF
    pdf_filename = f"appointment_report_{start_date}_to_{end_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    
    with open(pdf_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())
    
    # Create report record
    report = Report(
        child_id=child_id if child_id else None,
        report_type='appointment_report',
        title=f'Appointment Report ({start_date} to {end_date})',
        pdf_path=pdf_path,
        generated_by=f"{data.get('email')} ({role})"
    )
    db.session.add(report)
    db.session.commit()
    
    return jsonify({
        'report_id': report.id,
        'pdf_url': f'/api/reports/download/{report.id}',
        'filename': pdf_filename,
        'appointments_count': len(appointments)
    }), 200


# ============= VACCINATION SUMMARY REPORTS =============

@reports_bp.route('/vaccination-summary', methods=['POST'])
def generate_vaccination_summary_report():
    """Generate vaccination summary report"""
    data, role = get_auth_user()
    if not data or role not in ['admin', 'staff']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    req_data = request.get_json() or {}
    report_type = req_data.get('type', 'monthly')  # daily, weekly, monthly
    start_date = req_data.get('start_date')
    end_date = req_data.get('end_date')
    
    if report_type not in ['daily', 'weekly', 'monthly']:
        return jsonify({'error': 'Invalid report type'}), 400
    
    # Calculate date range if not provided
    today = date.today()
    if report_type == 'daily':
        start = end = today
    elif report_type == 'weekly':
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    else:  # monthly
        start = today.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400
    
    # Get vaccination statistics
    completed_vaccinations = VaccinationSchedule.query.filter(
        VaccinationSchedule.status == 'completed',
        VaccinationSchedule.completed_date >= start,
        VaccinationSchedule.completed_date <= end
    ).all()
    
    pending_vaccinations = VaccinationSchedule.query.filter(
        VaccinationSchedule.status == 'pending',
        VaccinationSchedule.scheduled_date <= end
    ).all()
    
    overdue_vaccinations = VaccinationSchedule.query.filter(
        VaccinationSchedule.status == 'pending',
        VaccinationSchedule.scheduled_date < today
    ).all()
    
    # Generate PDF
    from services.pdf_generator import generate_vaccination_summary_pdf
    pdf_buffer = generate_vaccination_summary_pdf(
        completed_vaccinations, pending_vaccinations, overdue_vaccinations,
        start, end, report_type
    )
    
    # Save PDF
    pdf_filename = f"vaccination_summary_{report_type}_{start}_{end}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
    
    with open(pdf_path, 'wb') as f:
        f.write(pdf_buffer.getvalue())
    
    # Create report record
    report = Report(
        report_type='vaccination_summary',
        title=f'Vaccination Summary Report ({report_type.title()})',
        pdf_path=pdf_path,
        generated_by=f"{data.get('email')} ({role})"
    )
    db.session.add(report)
    db.session.commit()
    
    return jsonify({
        'report_id': report.id,
        'pdf_url': f'/api/reports/download/{report.id}',
        'filename': pdf_filename,
        'summary': {
            'completed': len(completed_vaccinations),
            'pending': len(pending_vaccinations),
            'overdue': len(overdue_vaccinations),
            'period': f'{start} to {end}'
        }
    }), 200
