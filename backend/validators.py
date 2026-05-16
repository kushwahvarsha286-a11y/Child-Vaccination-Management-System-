"""
Input validation utilities for the vaccination management system.
Ensures all user inputs are validated before database operations.
"""
from datetime import datetime, date
import re

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class Validator:
    """Centralized validation class for all entities"""
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required and must be a string")
        
        # Simple email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email.strip()):
            raise ValidationError("Invalid email format")
        
        return email.strip()
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password or not isinstance(password, str):
            raise ValidationError("Password is required and must be a string")
        
        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters long")
        
        return password
    
    @staticmethod
    def validate_name(name, field_name="Name"):
        """Validate name field"""
        if not name or not isinstance(name, str):
            raise ValidationError(f"{field_name} is required and must be a string")
        
        name = name.strip()
        if len(name) < 2:
            raise ValidationError(f"{field_name} must be at least 2 characters")
        
        if len(name) > 100:
            raise ValidationError(f"{field_name} must not exceed 100 characters")
        
        return name
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number"""
        if phone is None:
            return None
        
        if not isinstance(phone, str):
            raise ValidationError("Phone must be a string")
        
        phone = phone.strip()
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\.]+', '', phone)
        
        # Phone should have at least 7 digits
        if not re.search(r'\d{7,}', cleaned):
            raise ValidationError("Phone number must contain at least 7 digits")
        
        return phone
    
    @staticmethod
    def validate_date_of_birth(dob_str):
        """Validate date of birth"""
        if not dob_str:
            raise ValidationError("Date of birth is required")
        
        try:
            if isinstance(dob_str, str):
                dob = datetime.fromisoformat(dob_str).date()
            elif isinstance(dob_str, date):
                dob = dob_str
            else:
                raise ValidationError("Date of birth must be a valid date")
            
            # Check if DOB is in the future
            if dob > date.today():
                raise ValidationError("Date of birth cannot be in the future")
            
            # Check if DOB is too far in the past (more than 120 years)
            age_threshold = date.today().replace(year=date.today().year - 120)
            if dob < age_threshold:
                raise ValidationError("Date of birth appears to be invalid (too far in past)")
            
            return dob
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    @staticmethod
    def validate_vaccination_date(vax_date_str):
        """Validate vaccination date"""
        if not vax_date_str:
            raise ValidationError("Vaccination date is required")
        
        try:
            if isinstance(vax_date_str, str):
                vax_date = datetime.fromisoformat(vax_date_str).date()
            elif isinstance(vax_date_str, date):
                vax_date = vax_date_str
            else:
                raise ValidationError("Vaccination date must be a valid date")
            
            # Check if vaccination date is too far in the future (more than 1 year)
            from datetime import timedelta
            max_future_date = date.today() + timedelta(days=365)
            if vax_date > max_future_date:
                raise ValidationError("Vaccination date cannot be more than 1 year in the future")
            
            return vax_date
        except ValueError:
            raise ValidationError("Invalid date format. Use YYYY-MM-DD")
    
    @staticmethod
    def validate_scheduled_datetime(scheduled_str):
        """Validate appointment scheduled datetime"""
        if not scheduled_str:
            raise ValidationError("Scheduled date/time is required")
        
        try:
            if isinstance(scheduled_str, str):
                scheduled = datetime.fromisoformat(scheduled_str)
            elif isinstance(scheduled_str, datetime):
                scheduled = scheduled_str
            else:
                raise ValidationError("Scheduled date/time must be a valid datetime")
            
            # Check if scheduled date is in the future
            if scheduled < datetime.utcnow():
                raise ValidationError("Appointment cannot be scheduled in the past")
            
            # Check if scheduled date is too far in the future (more than 1 year)
            from datetime import timedelta
            max_future_date = datetime.utcnow() + timedelta(days=365)
            if scheduled > max_future_date:
                raise ValidationError("Appointment cannot be scheduled more than 1 year in advance")
            
            return scheduled
        except ValueError:
            raise ValidationError("Invalid datetime format. Use ISO format (YYYY-MM-DDTHH:MM:SS)")
    
    @staticmethod
    def validate_gender(gender):
        """Validate gender field"""
        if gender is None:
            return None
        
        if not isinstance(gender, str):
            raise ValidationError("Gender must be a string")
        
        gender = gender.strip().lower()
        valid_genders = ['male', 'female', 'other']
        
        if gender not in valid_genders:
            raise ValidationError(f"Gender must be one of: {', '.join(valid_genders)}")
        
        return gender.capitalize()
    
    @staticmethod
    def validate_vaccination_status(status):
        """Validate vaccination status"""
        if status is None:
            return 'completed'
        
        if not isinstance(status, str):
            raise ValidationError("Status must be a string")
        
        valid_statuses = ['completed', 'pending', 'scheduled']
        status = status.strip().lower()
        
        if status not in valid_statuses:
            raise ValidationError(f"Status must be one of: {', '.join(valid_statuses)}")
        
        return status
    
    @staticmethod
    def validate_appointment_status(status):
        """Validate appointment status"""
        if status is None:
            return 'scheduled'
        
        if not isinstance(status, str):
            raise ValidationError("Status must be a string")
        
        valid_statuses = ['scheduled', 'completed', 'cancelled']
        status = status.strip().lower()
        
        if status not in valid_statuses:
            raise ValidationError(f"Status must be one of: {', '.join(valid_statuses)}")
        
        return status
    
    @staticmethod
    def validate_provider_type(provider_type):
        """Validate provider type"""
        if not provider_type or not isinstance(provider_type, str):
            raise ValidationError("Provider type is required")
        
        valid_types = ['hospital', 'clinic', 'private', 'pharmacy']
        provider_type = provider_type.strip().lower()
        
        if provider_type not in valid_types:
            raise ValidationError(f"Provider type must be one of: {', '.join(valid_types)}")
        
        return provider_type
    
    @staticmethod
    def validate_integer(value, field_name, min_val=None, max_val=None):
        """Validate integer field"""
        if value is None:
            return None
        
        try:
            as_int = int(value)
            
            if min_val is not None and as_int < min_val:
                raise ValidationError(f"{field_name} must be at least {min_val}")
            
            if max_val is not None and as_int > max_val:
                raise ValidationError(f"{field_name} must not exceed {max_val}")
            
            return as_int
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer")
    
    @staticmethod
    def validate_text(text, field_name, max_length=1000):
        """Validate text field"""
        if text is None:
            return None
        
        if not isinstance(text, str):
            raise ValidationError(f"{field_name} must be a string")
        
        text = text.strip()
        
        if len(text) > max_length:
            raise ValidationError(f"{field_name} must not exceed {max_length} characters")
        
        return text
    
    @staticmethod
    def validate_url(url):
        """Validate URL"""
        if url is None or url == '':
            return None
        
        if not isinstance(url, str):
            raise ValidationError("URL must be a string")
        
        url = url.strip()
        
        # Simple URL validation
        url_pattern = r'^https?:\/\/[^\s/$.?#].[^\s]*$'
        if not re.match(url_pattern, url, re.IGNORECASE):
            raise ValidationError("Invalid URL format. Must start with http:// or https://")
        
        return url


class ChildValidator(Validator):
    """Validator for Child entity"""
    
    @staticmethod
    def validate_child_data(data):
        """Validate child creation/update data"""
        errors = {}
        validated = {}
        
        # Validate required fields
        try:
            validated['name'] = Validator.validate_name(data.get('name'), 'Child name')
        except ValidationError as e:
            errors['name'] = str(e)
        
        try:
            validated['date_of_birth'] = Validator.validate_date_of_birth(data.get('date_of_birth'))
        except ValidationError as e:
            errors['date_of_birth'] = str(e)
        
        try:
            validated['parent_name'] = Validator.validate_name(data.get('parent_name'), 'Parent name')
        except ValidationError as e:
            errors['parent_name'] = str(e)
        
        try:
            validated['parent_email'] = Validator.validate_email(data.get('parent_email'))
        except ValidationError as e:
            errors['parent_email'] = str(e)
        
        # Validate optional fields
        if 'parent_phone' in data:
            try:
                validated['parent_phone'] = Validator.validate_phone(data.get('parent_phone'))
            except ValidationError as e:
                errors['parent_phone'] = str(e)
        
        if 'gender' in data:
            try:
                validated['gender'] = Validator.validate_gender(data.get('gender'))
            except ValidationError as e:
                errors['gender'] = str(e)
        
        if 'relation' in data:
            try:
                validated['relation'] = Validator.validate_name(data.get('relation'), 'Relation')
            except ValidationError as e:
                errors['relation'] = str(e)
        
        if errors:
            raise ValidationError(f"Validation failed: {errors}")
        
        return validated
