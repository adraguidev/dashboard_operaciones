class CustomError(Exception):
    """Base para errores personalizados"""
    pass

class DataLoadError(CustomError):
    """Error al cargar datos"""
    pass

def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error: {str(e)}")
            logger.error(f"Error en {func.__name__}: {str(e)}")
            return None
    return wrapper 