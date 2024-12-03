import os
import json
import streamlit as st
from google.oauth2 import service_account
from src.config.settings import GOOGLE_CREDENTIALS_FILE, GOOGLE_SCOPES
import pymongo

def get_google_credentials():
    """
    Obtiene las credenciales de Google, priorizando st.secrets para Streamlit Cloud
    y usando el archivo local solo como respaldo
    """
    # Primero intenta obtener las credenciales desde st.secrets (para Streamlit Cloud)
    if "gcp_service_account" in st.secrets:
        try:
            return service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=GOOGLE_SCOPES
            )
        except Exception as e:
            st.error(f"Error al obtener credenciales desde secrets: {str(e)}")
    
    # Si no hay secrets o fallan, intenta usar el archivo local
    try:
        # Intenta diferentes ubicaciones posibles del archivo
        possible_paths = [
            GOOGLE_CREDENTIALS_FILE,
            'migra2024-77aaf61899d3.json',
            os.path.join('credentials', 'migra2024-77aaf61899d3.json')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return service_account.Credentials.from_service_account_file(
                    path,
                    scopes=GOOGLE_SCOPES
                )
    except Exception as e:
        st.error(f"Error al leer archivo de credenciales: {str(e)}")
    
    raise FileNotFoundError(
        "No se encontraron credenciales válidas. "
        "En Streamlit Cloud, configura los secrets. "
        "En local, asegúrate de tener el archivo de credenciales en una ubicación válida."
    )

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