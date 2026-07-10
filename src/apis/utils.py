"""
API utilities for standardized responses, error handling, and validation.
"""
from functools import wraps
from typing import Any, Dict, Optional, Callable
from flask import jsonify, request
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class APIResponse:
    """Standardized API response format."""
    
    @staticmethod
    def success(data: Any, message: str = "Success", status_code: int = 200) -> tuple:
        """Return standardized success response."""
        return jsonify({
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }), status_code
    
    @staticmethod
    def error(message: str, error_code: str = "ERROR", status_code: int = 400, details: Optional[Dict] = None) -> tuple:
        """Return standardized error response."""
        response = {
            "status": "error",
            "message": message,
            "error_code": error_code,
            "timestamp": datetime.utcnow().isoformat()
        }
        if details:
            response["details"] = details
        return jsonify(response), status_code
    
    @staticmethod
    def created(data: Any, message: str = "Created", status_code: int = 201) -> tuple:
        """Return standardized created response."""
        return APIResponse.success(data, message, status_code)
    
    @staticmethod
    def no_content(status_code: int = 204) -> tuple:
        """Return no content response."""
        return "", status_code


class ValidationError(Exception):
    """Custom validation error."""
    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


class RequestValidator:
    """Validate incoming requests."""
    
    @staticmethod
    def validate_json_fields(required_fields: list) -> Callable:
        """Decorator to validate required JSON fields in request."""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                data = request.get_json(force=True, silent=True)
                
                if data is None:
                    return APIResponse.error(
                        "Request body must be valid JSON",
                        "INVALID_JSON",
                        400
                    )
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return APIResponse.error(
                        f"Missing required fields: {', '.join(missing_fields)}",
                        "MISSING_FIELDS",
                        400,
                        {"missing_fields": missing_fields}
                    )
                
                # Attach validated data to request
                request.validated_data = data
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @staticmethod
    def validate_query_params(required_params: list) -> Callable:
        """Decorator to validate required query parameters."""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def decorated_function(*args, **kwargs):
                missing_params = [param for param in required_params if param not in request.args]
                if missing_params:
                    return APIResponse.error(
                        f"Missing required query parameters: {', '.join(missing_params)}",
                        "MISSING_PARAMS",
                        400,
                        {"missing_params": missing_params}
                    )
                return f(*args, **kwargs)
            return decorated_function
        return decorator
    
    @staticmethod
    def validate_string_field(value: str, field_name: str, min_length: int = 1, max_length: int = None) -> str:
        """Validate a string field."""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string", field_name)
        
        if len(value.strip()) < min_length:
            raise ValidationError(f"{field_name} is too short (minimum {min_length})", field_name)
        
        if max_length and len(value) > max_length:
            raise ValidationError(f"{field_name} is too long (maximum {max_length})", field_name)
        
        return value.strip()
    
    @staticmethod
    def validate_project_name(project_name: str) -> str:
        """Validate project name."""
        from werkzeug.utils import secure_filename
        
        validated = RequestValidator.validate_string_field(project_name, "project_name", min_length=1, max_length=255)
        safe_name = secure_filename(validated)
        
        if not safe_name:
            raise ValidationError("project_name contains invalid characters", "project_name")
        
        return safe_name


def handle_api_errors(f: Callable) -> Callable:
    """Decorator to handle common API errors."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            return APIResponse.error(e.message, "VALIDATION_ERROR", 400, {"field": e.field})
        except ValueError as e:
            logger.warning(f"Value error: {str(e)}")
            return APIResponse.error(str(e), "VALUE_ERROR", 400)
        except FileNotFoundError as e:
            logger.warning(f"File not found: {str(e)}")
            return APIResponse.error("Resource not found", "NOT_FOUND", 404)
        except PermissionError as e:
            logger.warning(f"Permission denied: {str(e)}")
            return APIResponse.error("Permission denied", "PERMISSION_DENIED", 403)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return APIResponse.error(
                "An unexpected error occurred",
                "INTERNAL_ERROR",
                500,
                {"error_type": type(e).__name__}
            )
    return decorated_function


def log_request_response(f: Callable) -> Callable:
    """Decorator to log API requests and responses."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = datetime.utcnow()
        
        # Log request
        logger.debug(f"API Request: {request.method} {request.path}")
        logger.debug(f"Query params: {dict(request.args)}")
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                logger.debug(f"Request body: {request.get_json(silent=True)}")
            except:
                pass
        
        # Execute function
        response = f(*args, **kwargs)
        
        # Log response
        elapsed_time = (datetime.utcnow() - start_time).total_seconds()
        status_code = response[1] if isinstance(response, tuple) else 200
        logger.debug(f"API Response: {status_code} in {elapsed_time:.3f}s")
        
        return response
    return decorated_function
