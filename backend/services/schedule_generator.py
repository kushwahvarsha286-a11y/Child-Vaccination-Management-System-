from datetime import timedelta
from dateutil.relativedelta import relativedelta
from models import db, Vaccine, Vaccination, VaccinationSchedule

# Standard vaccination schedule based on WHO and Indian vaccination guidelines
STANDARD_VACCINATION_SCHEDULE = {
    'BCG': [0],  # Birth
    'Polio (IPV)': [2, 4, 6, 15],  # 2, 4, 6, 18 months
    'Pentavalent': [2, 4, 6, 15],  # 2, 4, 6, 18 months (DPT+HepB+Hib)
    'Rotavirus': [2, 4, 6],  # 2, 4, 6 months
    'Pneumococcal': [2, 4, 6, 12],  # 2, 4, 6, 12 months
    'Hepatitis B': [0, 1, 6],  # Birth, 1 month, 6 months
    'MMR': [12, 18],  # 12 months, 18 months
    'Varicella': [12, 18],  # 12 months, 18 months
}

def generate_vaccination_schedule(child):
    """
    Generate standard vaccination schedule for a newly registered child.
    Creates both Vaccination records (for backward compatibility) and 
    VaccinationSchedule records (for better tracking).
    
    Args:
        child: Child object
    """
    vaccines = Vaccine.query.all()
    vaccine_dict = {v.name: v for v in vaccines}
    
    # Create vaccination records based on standard schedule
    for vaccine_name, age_months_list in STANDARD_VACCINATION_SCHEDULE.items():
        vaccine = vaccine_dict.get(vaccine_name)
        if not vaccine:
            continue
        
        for idx, age_months in enumerate(age_months_list):
            # Calculate scheduled date: DOB + age_months
            scheduled_date = child.date_of_birth + relativedelta(months=age_months)
            
            # Create VaccinationSchedule record
            schedule = VaccinationSchedule(
                child_id=child.id,
                vaccine_id=vaccine.id,
                scheduled_date=scheduled_date,
                age_months=age_months,
                status='pending'
            )
            db.session.add(schedule)
            
            # Removed: Create Vaccination record for backward compatibility to avoid data sync issues
    
    return True


def get_next_vaccination(child):
    """
    Get the next pending vaccination for a child
    
    Args:
        child: Child object
        
    Returns:
        dict: Next vaccination details or None
    """
    from datetime import date
    next_vac = VaccinationSchedule.query.filter(
        VaccinationSchedule.child_id == child.id,
        VaccinationSchedule.status == 'pending',
        VaccinationSchedule.scheduled_date >= date.today()
    ).order_by(VaccinationSchedule.scheduled_date).first()
    
    if next_vac:
        return next_vac.to_dict()
    return None


def get_overdue_vaccinations(child):
    """
    Get all overdue vaccinations for a child
    
    Args:
        child: Child object
        
    Returns:
        list: List of overdue vaccinations
    """
    from datetime import date
    overdue = VaccinationSchedule.query.filter(
        VaccinationSchedule.child_id == child.id,
        VaccinationSchedule.status == 'pending',
        VaccinationSchedule.scheduled_date < date.today()
    ).all()
    
    return [v.to_dict() for v in overdue]


def get_vaccination_progress(child):
    """
    Get vaccination progress statistics for a child
    
    Args:
        child: Child object
        
    Returns:
        dict: Vaccination progress stats
    """
    total = VaccinationSchedule.query.filter_by(child_id=child.id).count()
    completed = VaccinationSchedule.query.filter_by(
        child_id=child.id, 
        status='completed'
    ).count()
    pending = VaccinationSchedule.query.filter_by(
        child_id=child.id, 
        status='pending'
    ).count()
    
    return {
        'total': total,
        'completed': completed,
        'pending': pending,
        'progress_percentage': round((completed / total * 100) if total > 0 else 0, 2)
    }

