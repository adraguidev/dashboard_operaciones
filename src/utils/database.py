import os
import json
import streamlit as st
from google.oauth2 import service_account
from src.config.settings import GOOGLE_SCOPES
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv

def get_google_credentials():
    """
    Obtiene las credenciales de Google desde los secrets de Streamlit
    """
    try:
        return service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=GOOGLE_SCOPES
        )
    except Exception as e:
        raise Exception(
            "Error al obtener credenciales desde Streamlit secrets. "
            "Asegúrate de configurar correctamente gcp_service_account en los secrets."
        )

def get_mongodb_connection():
    """Obtiene la conexión a MongoDB."""
    try:
        # Primero intenta desde secrets de Streamlit
        return MongoClient(st.secrets["connections"]["mongodb"]["uri"])
    except:
        # Si no está en la nube, usa variables de entorno
        load_dotenv()
        mongo_uri = os.getenv('MONGODB_URI')
        password = os.getenv('MONGODB_PASSWORD')
        if not mongo_uri or not password:
            raise ValueError("Credenciales de MongoDB no configuradas")
        return MongoClient(mongo_uri.replace('<db_password>', password))

@st.cache_resource
def init_connection():
    """Inicializa la conexión a MongoDB usando la función get_mongodb_connection"""
    return get_mongodb_connection()