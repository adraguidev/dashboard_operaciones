def get_google_credentials():
    """Obtiene las credenciales de Google desde secrets."""
    try:
        return st.secrets["gcp_service_account"]
    except Exception as e:
        logger.error(f"Error al obtener credenciales de Google: {str(e)}")
        return None 