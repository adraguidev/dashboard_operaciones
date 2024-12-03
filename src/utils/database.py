import os
import json
import streamlit as st
from google.oauth2 import service_account
from src.config.settings import GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES

def get_google_credentials():
    """
    Obtiene las credenciales de Google, ya sea desde st.secrets (cloud) 
    o desde el archivo local de credenciales
    """
    try:
        # Intenta obtener credenciales desde st.secrets
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=GOOGLE_SCOPES
        )
    except (KeyError, FileNotFoundError):
        # Si no hay secrets, busca el archivo de credenciales local
        if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
            raise FileNotFoundError(
                "No se encontraron credenciales ni en st.secrets ni en el archivo local"
            )
            
        credentials = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE,
            scopes=GOOGLE_SCOPES
        )
    
    return credentials

def get_mongodb_connection():
    """
    Obtiene la conexión a MongoDB, ya sea desde st.secrets (cloud)
    o desde variables de entorno locales
    """
    try:
        # Intenta obtener la URI desde st.secrets
        mongo_uri = st.secrets["connections"]["mongodb"]["uri"]
    except KeyError:
        # Si no hay secrets, busca en variables de entorno
        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise ValueError(
                "No se encontró la URI de MongoDB ni en st.secrets ni en variables de entorno"
            )
    
    return pymongo.MongoClient(mongo_uri)

@st.cache_resource
def init_connection():
    """Inicializa la conexión a MongoDB usando la función get_mongodb_connection"""
    return get_mongodb_connection() 