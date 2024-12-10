import logging
from typing import Optional, Callable, Any
from functools import wraps
import time

logger = logging.getLogger(__name__)

class OperationContext:
    """Contexto de la operación para mejor trazabilidad"""
    def __init__(self, operation_name: str, **metadata):
        self.operation_name = operation_name
        self.metadata = metadata
        self.start_time = time.time()

class CustomError(Exception):
    """Base para errores personalizados"""
    pass

class DataLoadError(CustomError):
    """Error al cargar datos"""
    pass

def handle_errors(error_message: Optional[str] = None):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            context = OperationContext(
                operation_name=func.__name__,
                args=str(args),
                kwargs=str(kwargs)
            )
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = error_message or f"Error en {func.__name__}"
                logger.exception(
                    error_msg,
                    extra={
                        "context": context.__dict__,
                        "error": str(e)
                    }
                )
                st.error(f"{error_msg}: {str(e)}")
                return None
        return wrapper
    return decorator