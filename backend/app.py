from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from config import DevelopmentConfig
from models import db, Child, Vaccine, Vaccination, Appointment, Provider, Notification, Staff, User, VaccinationSchedule
from routes.vaccination import vaccination_bp
from routes.appointment import appointment_bp
from routes.provider import provider_bp
from routes.notification import notification_bp
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.reports import reports_bp
from routes.admin import admin_bp
from routes.child import child_bp
from routes.staff import staff_bp
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
import jwt
from functools import wraps

def _verify_admin_token(token_str, secret_key):
    """Verify JWT token and check if user has admin role"""
    try:
        data = jwt.decode(token_str, secret_key, algorithms=['HS256'])
        return data.get('role') == 'admin', data
    except:
        return False, None

def create_app(config_class=DevelopmentConfig):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:5000",
                "http://127.0.0.1:5000"
            ],
            "allow_headers": ["Content-Type", "Authorization"],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "supports_credentials": True
        }
    })
    
    # Register blueprints
    app.register_blueprint(vaccination_bp)
    app.register_blueprint(appointment_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(notification_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(child_bp)
    app.register_blueprint(staff_bp)
    
    # Initialize Scheduler
    scheduler = BackgroundScheduler()
    
    def check_upcoming_vaccines_job():
        from services.mailer import send_vaccination_reminder
        with app.app_context():
            today = datetime.now(timezone.utc).date()
            reminder_date = today + timedelta(days=3) # Remind 3 days before
            
            # Find vaccinations due in 3 days OR due today
            upcoming_3days = VaccinationSchedule.query.filter_by(status='pending', scheduled_date=reminder_date).all()
            upcoming_today = VaccinationSchedule.query.filter_by(status='pending', scheduled_date=today).all()
            
            all_upcoming = upcoming_3days + upcoming_today
            
            for vac in all_upcoming:
                time_context = "in 3 days" if vac.scheduled_date == reminder_date else "TODAY"
                
                # Try sending email
                email_success = send_vaccination_reminder(
                    vac.child.parent_email, 
                    vac.child.name, 
                    vac.vaccine.name, 
                    vac.scheduled_date
                )
                
                status_str = 'Sent' if email_success else 'Failed'
                
                # Add notification
                msg = f"Reminder: {vac.vaccine.name} is due {time_context} ({vac.scheduled_date}) for {vac.child.name}"
                notif = Notification(
                    child_id=vac.child_id,
                    notification_type='vaccination_due',
                    title=f'Upcoming Vaccination ({time_context})',
                    message=msg,
                    delivery_status=status_str
                )
                db.session.add(notif)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error in cron job: {e}")

    scheduler.add_job(func=check_upcoming_vaccines_job, trigger="interval", hours=24)
    scheduler.start()
    
    # Create database tables
    with app.app_context():
        db.create_all()
        seed_sample_data()
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health():
        return jsonify({'status': 'healthy'}), 200
    
    # Dashboard stats endpoint
    @app.route('/api/dashboard/stats', methods=['GET'])
    def dashboard_stats():
        children_count = Child.query.count()
        vaccinations_count = Vaccination.query.count()
        appointments_count = Appointment.query.count()
        providers_count = Provider.query.count()
        pending_vaccinations = Vaccination.query.filter_by(status='pending').count()
        scheduled_appointments = Appointment.query.filter_by(status='scheduled').count()
        unread_notifications = Notification.query.filter_by(is_read=False).count()
        low_stock = Vaccine.query.filter(Vaccine.stock_quantity <= Vaccine.stock_threshold).count()
        return jsonify({
            'children': children_count,
            'vaccinations': vaccinations_count,
            'appointments': appointments_count,
            'providers': providers_count,
            'pending_vaccinations': pending_vaccinations,
            'scheduled_appointments': scheduled_appointments,
            'unread_notifications': unread_notifications,
            'low_stock_count': low_stock
        })
    
    # Vaccine stock endpoints
    @app.route('/api/vaccines/stock', methods=['GET'])
    def get_vaccine_stock():
        vaccines = Vaccine.query.all()
        return jsonify([v.to_dict() for v in vaccines])
    
    @app.route('/api/vaccines/stock/<int:vaccine_id>', methods=['PUT'])
    def update_vaccine_stock(vaccine_id):
        # Admin-only: verify JWT token has admin role
        auth = request.headers.get('Authorization') or request.headers.get('X-Admin-Token')
        if not auth:
            return jsonify({'error': 'Admin token required'}), 401
        
        token_str = auth.split(' ', 1)[1] if auth.startswith('Bearer ') else auth
        is_admin, token_data = _verify_admin_token(token_str, app.config.get('SECRET_KEY', 'dev-secret'))
        if not is_admin:
            return jsonify({'error': 'Forbidden - Admin access required'}), 403
        
        vaccine = Vaccine.query.get_or_404(vaccine_id)
        data = request.get_json()
        try:
            if 'stock_quantity' in data:
                vaccine.stock_quantity = data['stock_quantity']
            if 'stock_threshold' in data:
                vaccine.stock_threshold = data['stock_threshold']
            db.session.commit()
            
            # Create low-stock notification if needed
            if vaccine.stock_quantity <= vaccine.stock_threshold:
                notif = Notification(
                    child_id=1,
                    notification_type='low_stock',
                    title=f'Low Stock Alert: {vaccine.name}',
                    message=f'{vaccine.name} stock is low ({vaccine.stock_quantity} remaining). Threshold is {vaccine.stock_threshold}.'
                )
                db.session.add(notif)
                db.session.commit()
            
            return jsonify(vaccine.to_dict())
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    
    return app

def seed_sample_data():
    """Seed database with sample data if empty"""
    # Seed predefined Admin account
    from werkzeug.security import generate_password_hash
    if not Staff.query.filter_by(role='admin').first() and not User.query.filter_by(role='admin').first():
        admin = Staff(
            first_name='System',
            last_name='Admin',
            email=os.environ.get('ADMIN_EMAIL', 'admin@vaccicare.com'),
            password_hash=generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'Admin@1234')),
            role='admin',
            workplace='City Hospital',
            phone='+0-000-0000',
            specialty='System Administrator',
            status='approved'  # Admin is pre-approved
        )
        db.session.add(admin)
        db.session.commit()
        print("[OK] Default admin account seeded successfully")

    if Vaccine.query.first() is None:
        vaccines = [
            Vaccine(name='BCG', description='Bacille Calmette-Guérin vaccine', recommended_age_months=0, stock_quantity=150, stock_threshold=30),
            Vaccine(name='Polio (IPV)', description='Inactivated Polio Vaccine', recommended_age_months=2, stock_quantity=200, stock_threshold=40),
            Vaccine(name='Pentavalent', description='DPT+HepB+Hib vaccine', recommended_age_months=2, stock_quantity=180, stock_threshold=35),
            Vaccine(name='Rotavirus', description='Rotavirus vaccine', recommended_age_months=2, stock_quantity=120, stock_threshold=25),
            Vaccine(name='Pneumococcal', description='Pneumococcal conjugate vaccine', recommended_age_months=2, stock_quantity=15, stock_threshold=20),
            Vaccine(name='MMR', description='Measles, Mumps, Rubella vaccine', recommended_age_months=12, stock_quantity=90, stock_threshold=20),
            Vaccine(name='Varicella', description='Chickenpox vaccine', recommended_age_months=12, stock_quantity=8, stock_threshold=15),
            Vaccine(name='Hepatitis B', description='Hepatitis B vaccine', recommended_age_months=0, stock_quantity=250, stock_threshold=50),
        ]
        db.session.add_all(vaccines)
        db.session.commit()
    
    # Ensure only City Hospital exists as the single provider
    city_hospital = Provider.query.filter_by(name='City Hospital').first()
    if not city_hospital:
        # Remove any legacy providers
        Provider.query.delete()
        city_hospital = Provider(
            name='City Hospital',
            provider_type='hospital',
            address='123 Healthcare Avenue, Medical District',
            phone='+91-9876543210',
            email='info@cityhospital.com',
            website='www.cityhospital.com'
        )
        db.session.add(city_hospital)
        db.session.commit()
        print("[OK] City Hospital provider seeded successfully")

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
