"""
QR Code Generator Service
Generates QR codes for vaccination certificates and verification
"""

import qrcode
import io
import base64
from datetime import datetime


def generate_certificate_qr(child_id, report_id, child_name):
    """
    Generate QR code for vaccination certificate
    
    Args:
        child_id: Child database ID
        report_id: Report database ID
        child_name: Child name for verification
        
    Returns:
        tuple: (qr_image_base64, qr_string)
    """
    # Create QR data string
    qr_data = f"VACCICARE|Child_ID:{child_id}|Report_ID:{report_id}|Name:{child_name}|Date:{datetime.now().isoformat()}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=4,
        border=2,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.read()).decode()
    
    return img_base64, qr_data


def generate_verification_code(report_id):
    """
    Generate a unique verification code for a report
    
    Args:
        report_id: Report database ID
        
    Returns:
        str: Verification code
    """
    import hashlib
    unique_string = f"{report_id}-{datetime.now().isoformat()}"
    verification_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:12].upper()
    return verification_hash
