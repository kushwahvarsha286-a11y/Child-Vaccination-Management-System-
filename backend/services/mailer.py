import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging

logging.basicConfig(level=logging.INFO)

def send_vaccination_reminder(to_email, child_name, vaccine_name, scheduled_date):
    """
    Sends an email reminder to parents about upcoming vaccinations.
    Fallback to Console logging if SMTP credentials are not found.
    """
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    
    subject = "Child Vaccination Reminder"
    body = f"""Dear Parent,

Your child {child_name} has an upcoming vaccination.

Vaccine: {vaccine_name}
Date: {scheduled_date.strftime('%Y-%m-%d')}

Please visit the healthcare center on time.

Thank you.
"""
    
    if not smtp_server or not smtp_user or not smtp_pass:
        logging.info("\n========== MOCK EMAIL DELIVERED ==========")
        logging.info(f"To: {to_email}")
        logging.info(f"Subject: {subject}")
        logging.info(f"Body: \n{body}")
        logging.info("==========================================\n")
        return True
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logging.error(f"Failed to send email to {to_email}: {e}")
        return False

def send_staff_approval_notification(to_email, staff_name, staff_id, temp_password):
    """
    Sends email to staff when their account is approved with login credentials.
    """
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    
    subject = "VacciCare Account Approved - Login Credentials"
    body = f"""Dear {staff_name},

Congratulations! Your VacciCare staff account has been approved by the administrator.

Your Login Credentials:
Email: {to_email}
Staff ID: {staff_id}
Temporary Password: {temp_password}

Please login using these credentials and change your password immediately upon first login.

Access VacciCare at: http://localhost:8000

Thank you for joining our healthcare team.

VacciCare Team
"""
    
    if not smtp_server or not smtp_user or not smtp_pass:
        logging.info("\n========== MOCK EMAIL DELIVERED (STAFF APPROVAL) ==========")
        logging.info(f"To: {to_email}")
        logging.info(f"Subject: {subject}")
        logging.info(f"Body: \n{body}")
        logging.info("============================================================\n")
        return True
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logging.error(f"Failed to send approval email to {to_email}: {e}")
        return False

def send_staff_rejection_notification(to_email, staff_name, reason=''):
    """
    Sends email to staff when their account is rejected.
    """
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_user = os.environ.get('SMTP_USER')
    smtp_pass = os.environ.get('SMTP_PASS')
    
    subject = "VacciCare Account Registration - Status Update"
    body = f"""Dear {staff_name},

Your VacciCare staff account registration has been reviewed by the administrator.

Status: REJECTED

"""
    if reason:
        body += f"Reason: {reason}\n\n"
    
    body += """If you believe this is an error or would like to reapply, please contact the administrator.

VacciCare Team
"""
    
    if not smtp_server or not smtp_user or not smtp_pass:
        logging.info("\n========== MOCK EMAIL DELIVERED (STAFF REJECTION) ==========")
        logging.info(f"To: {to_email}")
        logging.info(f"Subject: {subject}")
        logging.info(f"Body: \n{body}")
        logging.info("============================================================\n")
        return True
        
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, int(smtp_port))
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logging.error(f"Failed to send rejection email to {to_email}: {e}")
        return False
