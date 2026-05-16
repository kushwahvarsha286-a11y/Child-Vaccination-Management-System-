from datetime import datetime, timezone, date
from flask_sqlalchemy import SQLAlchemy
from dateutil.relativedelta import relativedelta

db = SQLAlchemy()

class User(db.Model):
    """Model for standard users (like Parents or Admins)"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='parent') # admin, parent
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'role': self.role,
            'phone': self.phone,
            'address': self.address,
            'created_at': self.created_at.isoformat()
        }

class Staff(db.Model):
    """Model for healthcare staff and providers"""
    __tablename__ = 'staff'
    
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='staff')
    workplace = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    specialty = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    staff_id = db.Column(db.String(20), unique=True, nullable=True)  # STAF-2026-001
    temp_password = db.Column(db.String(255), nullable=True)  # hashed temporary password
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'role': self.role,
            'workplace': self.workplace,
            'phone': self.phone,
            'specialty': self.specialty,
            'status': self.status,
            'staff_id': self.staff_id,
            'created_at': self.created_at.isoformat()
        }

class Child(db.Model):
    """Model for child records"""
    __tablename__ = 'child'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10))
    parent_name = db.Column(db.String(100), nullable=False)
    parent_email = db.Column(db.String(100), index=True, nullable=False)
    parent_phone = db.Column(db.String(20))
    relation = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    vaccinations = db.relationship('Vaccination', backref='child', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='child', lazy=True, cascade='all, delete-orphan')
    vaccination_schedules = db.relationship('VaccinationSchedule', backref='child', lazy=True, cascade='all, delete-orphan')
    reports = db.relationship('Report', backref='child', lazy=True, cascade='all, delete-orphan')
    
    def _ensure_date(self, dob):
        if isinstance(dob, str):
            try:
                return datetime.strptime(dob.split('T')[0], '%Y-%m-%d').date()
            except Exception:
                return date.today()
        return dob

    def get_age_months(self):
        """Calculate age in months"""
        today = date.today()
        dob = self._ensure_date(self.date_of_birth)
        age_delta = relativedelta(today, dob)
        return age_delta.years * 12 + age_delta.months
    
    def get_age_years(self):
        """Calculate age in years"""
        today = date.today()
        dob = self._ensure_date(self.date_of_birth)
        return (today.year - dob.year - 
                ((today.month, today.day) < (dob.month, dob.day)))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'date_of_birth': self.date_of_birth.isoformat(),
            'gender': self.gender,
            'parent_name': self.parent_name,
            'parent_email': self.parent_email,
            'parent_phone': self.parent_phone,
            'relation': self.relation,
            'age_months': self.get_age_months(),
            'age_years': self.get_age_years(),
            'created_at': self.created_at.isoformat()
        }

class Vaccine(db.Model):
    """Model for vaccine types"""
    __tablename__ = 'vaccine'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    recommended_age_months = db.Column(db.Integer)  # Age in months when vaccine is recommended
    stock_quantity = db.Column(db.Integer, default=100)
    stock_threshold = db.Column(db.Integer, default=20)  # Alert when stock falls below this
    
    vaccinations = db.relationship('Vaccination', backref='vaccine', lazy=True)
    appointments = db.relationship('Appointment', backref='vaccine', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'recommended_age_months': self.recommended_age_months,
            'stock_quantity': self.stock_quantity,
            'stock_threshold': self.stock_threshold
        }

class Vaccination(db.Model):
    """Model for vaccination records"""
    __tablename__ = 'vaccination'
    
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    vaccine_id = db.Column(db.Integer, db.ForeignKey('vaccine.id'), nullable=False)
    vaccination_date = db.Column(db.Date, nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider.id'))
    status = db.Column(db.String(20), default='completed')  # completed, pending
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'child_name': self.child.name if self.child else None,
            'vaccine_name': self.vaccine.name if self.vaccine else None,
            'vaccine_id': self.vaccine_id,
            'vaccination_date': self.vaccination_date.isoformat(),
            'provider_id': self.provider_id,
            'provider_name': self.provider.name if self.provider else None,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

class Provider(db.Model):
    """Model for healthcare providers (doctors, clinics)"""
    __tablename__ = 'provider'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    provider_type = db.Column(db.String(50))  # hospital, clinic, private practice
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    website = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    vaccinations = db.relationship('Vaccination', backref='provider', lazy=True)
    appointments = db.relationship('Appointment', backref='provider', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'provider_type': self.provider_type,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'created_at': self.created_at.isoformat()
        }

class Appointment(db.Model):
    """Model for vaccination appointments"""
    __tablename__ = 'appointment'
    
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider.id'), nullable=False)
    scheduled_date = db.Column(db.DateTime, index=True, nullable=False)
    vaccine_id = db.Column(db.Integer, db.ForeignKey('vaccine.id'))
    status = db.Column(db.String(20), index=True, default='scheduled')  # scheduled, completed, cancelled
    notes = db.Column(db.Text)
    cancellation_reason = db.Column(db.Text)  # Reason for cancellation if cancelled
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'child_name': self.child.name if self.child else None,
            'provider_id': self.provider_id,
            'provider_name': self.provider.name if self.provider else None,
            'scheduled_date': self.scheduled_date.isoformat(),
            'vaccine_name': self.vaccine.name if self.vaccine else None,
            'status': self.status,
            'notes': self.notes,
            'cancellation_reason': self.cancellation_reason,
            'created_at': self.created_at.isoformat()
        }

class Notification(db.Model):
    """Model for notifications"""
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), index=True, nullable=False)
    notification_type = db.Column(db.String(50), index=True)  # appointment_reminder, vaccination_due
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    delivery_status = db.Column(db.String(50), default='Pending') # Pending, Sent, Failed
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'notification_type': self.notification_type,
            'title': self.title,
            'message': self.message,
            'is_read': self.is_read,
            'delivery_status': self.delivery_status,
            'created_at': self.created_at.isoformat()
        }


class VaccinationSchedule(db.Model):
    """Model for standard vaccination schedules"""
    __tablename__ = 'vaccination_schedule'
    
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), index=True, nullable=False)
    vaccine_id = db.Column(db.Integer, db.ForeignKey('vaccine.id'), nullable=False)
    scheduled_date = db.Column(db.Date, index=True, nullable=False)
    age_months = db.Column(db.Integer)  # Age in months when vaccine should be given
    status = db.Column(db.String(20), index=True, default='pending')  # pending, completed, skipped, delayed
    completed_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    vaccine = db.relationship('Vaccine', backref='schedules')

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'vaccine_id': self.vaccine_id,
            'vaccine_name': self.vaccine.name if self.vaccine else None,
            'scheduled_date': self.scheduled_date.isoformat(),
            'age_months': self.age_months,
            'status': self.status,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'created_at': self.created_at.isoformat()
        }


class Report(db.Model):
    """Model for vaccination reports and certificates"""
    __tablename__ = 'report'
    
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    report_type = db.Column(db.String(50), default='vaccination_certificate')  # vaccination_certificate, progress_report
    title = db.Column(db.String(200), nullable=False)
    pdf_path = db.Column(db.String(255))  # Path to stored PDF
    qr_code = db.Column(db.String(500))  # QR code data for verification
    generated_by = db.Column(db.String(100))  # Staff/Provider name
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    signature = db.Column(db.Text)  # Digital signature placeholder
    is_valid = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    
    staff = db.relationship('Staff', backref='reports')

    def to_dict(self):
        return {
            'id': self.id,
            'child_id': self.child_id,
            'report_type': self.report_type,
            'title': self.title,
            'pdf_path': self.pdf_path,
            'qr_code': self.qr_code,
            'generated_by': self.generated_by,
            'is_valid': self.is_valid,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class AuditLog(db.Model):
    """Model for audit logging and system activity tracking"""
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    user_type = db.Column(db.String(20))  # user, staff
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))  # child, vaccination, appointment, etc
    entity_id = db.Column(db.Integer)
    changes = db.Column(db.Text)  # JSON format of what changed
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_type': self.user_type,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'changes': self.changes,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }

