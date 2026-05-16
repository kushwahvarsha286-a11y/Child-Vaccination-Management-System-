import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import qrcode
from datetime import datetime
from dateutil.relativedelta import relativedelta

def generate_vaccination_certificate(child, vaccinations, parent_name=None):
    """
    Generates a professional PDF vaccination certificate using ReportLab.

    Args:
        child:        Child model object  (provides child.name, child.date_of_birth, etc.)
        vaccinations: List of VaccinationSchedule (or compatible) objects to display.
        parent_name:  Full name of the logged-in parent/guardian fetched from the User
                      table by the calling route.  This is completely separate from
                      child.parent_name and must NOT default to it.

    Returns:
        A BytesIO buffer containing the PDF data.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50
    )

    # ── Styles ──────────────────────────────────────────────────────────────
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontSize=22, alignment=1, spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, alignment=1, textColor=colors.gray, spaceAfter=4
    )
    generated_style = ParagraphStyle(
        'Generated', parent=styles['Normal'],
        fontSize=10, alignment=1,
        textColor=colors.darkblue, spaceAfter=24
    )
    header_style = ParagraphStyle(
        'Header', parent=styles['Heading2'],
        fontSize=13, spaceAfter=8, textColor=colors.darkblue
    )
    normal_style = styles['Normal']

    elements = []

    # ── 1. HEADER ────────────────────────────────────────────────────────────
    generation_timestamp = datetime.now().strftime('%B %d, %Y  %I:%M %p')

    elements.append(Paragraph("<b>VacciCare — Official Vaccination Certificate</b>", title_style))
    elements.append(Paragraph("Authorized Child Immunization Record", subtitle_style))
    elements.append(Paragraph(
        f"<b>Certificate Generated:</b> {generation_timestamp}",
        generated_style
    ))

    # ── 2. CHILD & PARENT INFORMATION ────────────────────────────────────────
    elements.append(Paragraph("<b>Child &amp; Parent Information</b>", header_style))

    # Calculate child's current age
    age = relativedelta(datetime.now().date(), child.date_of_birth)
    age_str = f"{age.years} yr {age.months} mo"

    # ── IMPORTANT: parent_name comes ONLY from the logged-in User record ──
    #    It is NEVER taken from child.parent_name.
    safe_parent_name = str(parent_name).strip() if parent_name else "N/A"
    safe_child_name  = child.name.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')

    child_info_data = [
        # Row 1: Child Name  |  Parent / Guardian Name
        ["Child Name:",  safe_child_name,  "Parent / Guardian Name:",  safe_parent_name],
        # Row 2: Gender     |  Date of Birth
        ["Gender:",      child.gender.capitalize() if child.gender else "Not specified",
         "Date of Birth:", child.date_of_birth.strftime('%d %B %Y')],
        # Row 3: Age        |  Child registered on
        ["Current Age:", age_str,
         "Registered On:", child.created_at.strftime('%d %B %Y') if child.created_at else "Unknown"],
    ]

    t_info = Table(child_info_data, colWidths=[120, 160, 130, 130])
    t_info.setStyle(TableStyle([
        ('FONTNAME',    (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME',    (0, 0), (0, -1), 'Helvetica-Bold'),   # label column 1
        ('FONTNAME',    (2, 0), (2, -1), 'Helvetica-Bold'),   # label column 3
        ('TEXTCOLOR',   (0, 0), (-1, -1), colors.black),
        ('ALIGN',       (0, 0), (-1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',  (0, 0), (-1, -1), 4),
        ('BACKGROUND',  (0, 0), (-1, -1), colors.Color(0.95, 0.97, 1.0)),
        ('GRID',        (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 24))

    # ── 3. COMPLETED VACCINATIONS ONLY ───────────────────────────────────────
    elements.append(Paragraph("<b>Completed Vaccination History</b>", header_style))

    # Filter to only COMPLETED vaccinations; sort by scheduled date
    completed_vacs = [v for v in vaccinations if str(v.status).lower() == 'completed']
    completed_vacs.sort(key=lambda x: x.scheduled_date)

    table_data = [["#", "Vaccine Name", "Scheduled Date", "Completion Date"]]

    if completed_vacs:
        for idx, vac in enumerate(completed_vacs, start=1):
            vaccine_name   = vac.vaccine.name if vac.vaccine else "Unknown"
            scheduled_date = vac.scheduled_date.strftime('%d %b %Y')

            # Use the actual stored completion date when available;
            # fall back to scheduled_date only as a last resort.
            if hasattr(vac, 'completed_date') and vac.completed_date:
                comp_date = vac.completed_date.strftime('%d %b %Y')
            else:
                comp_date = scheduled_date   # best known date for completed record

            table_data.append([str(idx), vaccine_name, scheduled_date, comp_date])
    else:
        table_data.append(["–", "No completed vaccinations on record", "–", "–"])

    t_records = Table(table_data, colWidths=[30, 180, 120, 120])
    t_records.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',    (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING',    (0, 0), (-1, 0), 10),
        # Data rows
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',      (0, 1), (-1, -1), 9),
        ('BACKGROUND',    (0, 1), (-1, -1), colors.Color(0.97, 1.0, 0.97)),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.Color(0.97, 1.0, 0.97), colors.Color(0.92, 0.97, 0.92)]),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN',         (1, 1), (1, -1), 'LEFT'),   # vaccine name left-aligned
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
    ]))
    elements.append(t_records)

    # Completed count summary
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"Total completed vaccinations: <b>{len(completed_vacs)}</b>",
        normal_style
    ))
    elements.append(Spacer(1, 32))

    # ── 4. QR CODE & LEGAL FOOTER ────────────────────────────────────────────
    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(
        f"VacciCare Certificate | Child: {child.name} | ID: {child.id} | "
        f"Parent: {safe_parent_name} | Generated: {generation_timestamp}"
    )
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")

    qr_buffer = io.BytesIO()
    img_qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_img = Image(qr_buffer, width=70, height=70)

    cert_text = (
        "This document is an official VacciCare vaccination certificate. "
        "It certifies that the child named above has received all listed "
        "vaccinations as per the authorized medical schedule. "
        "Please retain this certificate for school admissions, travel, "
        "and public health records."
    )

    footer_data = [[qr_img, Paragraph(f"<i>{cert_text}</i>", normal_style)]]
    t_footer = Table(footer_data, colWidths=[85, 430])
    t_footer.setStyle(TableStyle([
        ('ALIGN',  (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(t_footer)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_appointment_report_pdf(appointments, start_date, end_date, child_id=None):
    """
    Generates a PDF report for appointments within a date range.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, alignment=1, spaceAfter=20)
    header_style = ParagraphStyle('Header', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    normal_style = styles['Normal']
    
    elements = []
    
    # Title
    title = "Appointment Report"
    if child_id:
        title += f" for Child ID: {child_id}"
    elements.append(Paragraph(f"<b>{title}</b>", title_style))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", normal_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}", normal_style))
    elements.append(Spacer(1, 20))
    
    if not appointments:
        elements.append(Paragraph("No appointments found for the selected period.", normal_style))
    else:
        # Table data
        data = [['Date', 'Time', 'Child Name', 'Provider', 'Vaccine', 'Status', 'Notes']]
        
        for apt in appointments:
            time_str = apt.scheduled_date.strftime('%H:%M') if apt.scheduled_date else ''
            vaccine_name = apt.vaccine.name if apt.vaccine else 'General Checkup'
            notes = apt.notes[:50] + '...' if apt.notes and len(apt.notes) > 50 else apt.notes or ''
            
            data.append([
                apt.scheduled_date.strftime('%Y-%m-%d'),
                time_str,
                apt.child.name if apt.child else 'Unknown',
                apt.provider.name if apt.provider else 'Unknown',
                vaccine_name,
                apt.status.title(),
                notes
            ])
        
        # Create table
        col_widths = [70, 50, 100, 100, 80, 60, 80]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(f"Total Appointments: {len(appointments)}", normal_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_vaccination_summary_pdf(completed, pending, overdue, start_date, end_date, report_type):
    """
    Generates a PDF summary report for vaccinations.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=20, alignment=1, spaceAfter=20)
    header_style = ParagraphStyle('Header', parent=styles['Heading2'], fontSize=14, spaceAfter=10)
    normal_style = styles['Normal']
    
    elements = []
    
    # Title
    elements.append(Paragraph("<b>Vaccination Summary Report</b>", title_style))
    elements.append(Paragraph(f"Report Type: {report_type.title()}", normal_style))
    elements.append(Paragraph(f"Period: {start_date} to {end_date}", normal_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y %H:%M')}", normal_style))
    elements.append(Spacer(1, 20))
    
    # Summary statistics
    elements.append(Paragraph("<b>Summary Statistics</b>", header_style))
    
    stats_data = [
        ['Metric', 'Count'],
        ['Completed Vaccinations', str(len(completed))],
        ['Pending Vaccinations', str(len(pending))],
        ['Overdue Vaccinations', str(len(overdue))],
        ['Total', str(len(completed) + len(pending) + len(overdue))]
    ]
    
    stats_table = Table(stats_data, colWidths=[200, 100])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    
    elements.append(stats_table)
    elements.append(Spacer(1, 20))
    
    # Completed vaccinations section
    if completed:
        elements.append(Paragraph("<b>Completed Vaccinations</b>", header_style))
        comp_data = [['Date', 'Child Name', 'Vaccine', 'Provider']]
        
        for vac in completed[:50]:  # Limit to first 50 for readability
            provider_name = vac.child.vaccinations[0].provider.name if vac.child and vac.child.vaccinations else 'Unknown'
            comp_data.append([
                vac.completed_date.strftime('%Y-%m-%d') if vac.completed_date else '',
                vac.child.name if vac.child else 'Unknown',
                vac.vaccine.name if vac.vaccine else 'Unknown',
                provider_name
            ])
        
        comp_table = Table(comp_data, colWidths=[80, 120, 120, 120])
        comp_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.green),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        
        elements.append(comp_table)
        if len(completed) > 50:
            elements.append(Paragraph(f"... and {len(completed) - 50} more completed vaccinations", normal_style))
        elements.append(Spacer(1, 15))
    
    # Overdue vaccinations section
    if overdue:
        elements.append(Paragraph("<b>Overdue Vaccinations</b>", header_style))
        overdue_data = [['Scheduled Date', 'Child Name', 'Vaccine', 'Days Overdue']]
        
        today = datetime.now().date()
        for vac in overdue[:30]:  # Limit to first 30
            days_overdue = (today - vac.scheduled_date).days
            overdue_data.append([
                vac.scheduled_date.strftime('%Y-%m-%d'),
                vac.child.name if vac.child else 'Unknown',
                vac.vaccine.name if vac.vaccine else 'Unknown',
                str(days_overdue)
            ])
        
        overdue_table = Table(overdue_data, colWidths=[90, 120, 120, 80])
        overdue_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.red),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        
        elements.append(overdue_table)
        if len(overdue) > 30:
            elements.append(Paragraph(f"... and {len(overdue) - 30} more overdue vaccinations", normal_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
