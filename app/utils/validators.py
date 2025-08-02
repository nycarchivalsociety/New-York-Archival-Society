# app/utils/validators.py

import re
import uuid
from typing import Any, Dict, Optional
from flask import request
from functools import wraps
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def validate_uuid(value: str) -> bool:
    """Validate if string is a valid UUID"""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def validate_fee(fee: Any) -> bool:
    """Validate fee is a positive number"""
    try:
        fee_float = float(fee)
        return fee_float > 0
    except (ValueError, TypeError):
        return False

def validate_paypal_order_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate PayPal order creation data"""
    errors = {}
    
    if not data:
        raise ValidationError("No data provided")
    
    # Validate item_id
    item_id = data.get('item_id')
    if not item_id:
        errors['item_id'] = 'Item ID is required'
    elif not isinstance(item_id, str) or len(item_id.strip()) == 0:
        errors['item_id'] = 'Item ID must be a non-empty string'
    
    # Validate fee
    fee = data.get('fee')
    if fee is None:
        errors['fee'] = 'Fee is required'
    elif not validate_fee(fee):
        errors['fee'] = 'Fee must be a positive number'
    
    if errors:
        raise ValidationError(f"Validation errors: {errors}")
    
    return {
        'item_id': str(item_id).strip(),
        'fee': float(fee)
    }

def validate_capture_order_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate PayPal order capture data"""
    errors = {}
    
    if not data:
        raise ValidationError("No data provided")
    
    # Validate item_id
    item_id = data.get('item_id')
    if not item_id:
        errors['item_id'] = 'Item ID is required'
    elif not isinstance(item_id, str) or len(item_id.strip()) == 0:
        errors['item_id'] = 'Item ID must be a non-empty string'
    
    # Validate fee
    fee = data.get('fee')
    if fee is None:
        errors['fee'] = 'Fee is required'
    elif not validate_fee(fee):
        errors['fee'] = 'Fee must be a positive number'
    
    # Validate pickup (optional)
    pickup = data.get('pickup', False)
    if not isinstance(pickup, bool):
        errors['pickup'] = 'Pickup must be a boolean value'
    
    if errors:
        raise ValidationError(f"Validation errors: {errors}")
    
    return {
        'item_id': str(item_id).strip(),
        'fee': float(fee),
        'pickup': pickup
    }

def validate_pagination_params(page: Any, per_page: Any, max_per_page: int = 100) -> Dict[str, int]:
    """Validate pagination parameters"""
    try:
        page_int = int(page) if page else 1
        per_page_int = int(per_page) if per_page else 20
        
        # Ensure positive values
        page_int = max(1, page_int)
        per_page_int = max(1, min(per_page_int, max_per_page))
        
        return {
            'page': page_int,
            'per_page': per_page_int
        }
    except (ValueError, TypeError):
        return {
            'page': 1,
            'per_page': 20
        }

def require_json(f):
    """Decorator to ensure request has JSON content type"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            logger.warning(f"Non-JSON request to {request.endpoint} from {request.remote_addr}")
            return {'error': 'Content-Type must be application/json'}, 400
        return f(*args, **kwargs)
    return decorated_function

def validate_request_size(max_size: int = 1024 * 1024):  # 1MB default
    """Decorator to validate request content length"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.content_length and request.content_length > max_size:
                logger.warning(f"Request too large: {request.content_length} bytes from {request.remote_addr}")
                return {'error': 'Request too large'}, 413
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_string(value: str, max_length: int = 1000) -> str:
    """Sanitize string input by trimming and limiting length"""
    if not isinstance(value, str):
        return ""
    
    # Remove null bytes and control characters except newlines and tabs
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
    
    # Trim whitespace and limit length
    return sanitized.strip()[:max_length]