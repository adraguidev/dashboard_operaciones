import os
from dataclasses import dataclass
from typing import Dict, List
import streamlit as st

@dataclass
class ModuleConfig:
    """Configuración para cada módulo del sistema."""
    name: str
    icon: str
    folder: str
    inactive_evaluators: List[str]

# Módulos disponibles en la aplicación
MODULES = {
    'CCM': '📋 CCM',           # Calidad Migratoria
    'PRR': '🔄 PRR',           # Prórroga de Residencia
    'CCM-ESP': '⭐ CCM-ESP',    # Calidad Migratoria Especial
    'CCM-LEY': '⚖️ CCM-LEY',   # Calidad Migratoria Ley
    'SOL': '📝 SOL',           # Solicitudes
    'SPE': '🌟 SPE'            # Sistema de Permisos Especiales
}

# Configuración detallada de módulos
MODULES_CONFIG: Dict[str, ModuleConfig] = {
    'CCM': ModuleConfig(
        name='CCM',
        icon='📊',
        folder='descargas/CCM',
        inactive_evaluators=[
            "Mauricio Romero, Hugo",
            "Ugarte Sánchez, Paulo César",
            "Santibañez Chafalote, Lila Mariella",
            "Quispe Orosco, Karina Wendy",
            "Miranda Avila, Marco Antonio",
            "Aponte Sanchez, Paola Lita",
            "Orcada Herrera, Javier Eduardo",
            "Gomez Vera, Marcos Alberto",
            "VULNERABILIDAD",
            "SUSPENDIDA"
        ]
    ),
    'PRR': ModuleConfig(
        name='PRR',
        icon='🔄',
        folder='descargas/PRR',
        inactive_evaluators=[]
    ),
    'CCM-ESP': ModuleConfig(
        name='CCM-ESP',
        icon='⭐',
        folder='descargas/CCM-ESP',
        inactive_evaluators=[
            "Mauricio Romero, Hugo",
            "Ugarte Sánchez, Paulo César",
            "Santibañez Chafalote, Lila Mariella",
            "Quispe Orosco, Karina Wendy",
            "Miranda Avila, Marco Antonio",
            "Aponte Sanchez, Paola Lita",
            "Orcada Herrera, Javier Eduardo",
            "Gomez Vera, Marcos Alberto",
            "VULNERABILIDAD",
            "SUSPENDIDA"
        ]
    ),
    'CCM-LEY': ModuleConfig(
        name='CCM-LEY',
        icon='⚖️',
        folder='descargas/CCM-LEY',
        inactive_evaluators=[]
    ),
    'SOL': ModuleConfig(
        name='SOL',
        icon='📂',
        folder='descargas/SOL',
        inactive_evaluators=[]
    ),
    'SPE': ModuleConfig(
        name='SPE',
        icon='💼',
        folder='descargas/SPE',
        inactive_evaluators=[]
    )
}

# Configuración de Google Sheets
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Configuración de MongoDB
MONGODB_COLLECTIONS = {
    'CCM': 'consolidado_ccm',
    'PRR': 'consolidado_prr',
    'CCM-ESP': 'consolidado_ccm_esp',
    'CCM-LEY': 'consolidado_ccm',  # Usa la misma colección que CCM
    'SOL': 'consolidado_sol',
    'SPE': 'consolidado_spe',
    'RANKINGS': 'rankings'
}

# Columnas de fecha que deben ser procesadas
DATE_COLUMNS = [
    'FechaExpendiente',
    'FechaEtapaAprobacionMasivaFin',
    'FechaPre',
    'FechaTramite',
    'FechaAsignacion',
    'FECHA DE TRABAJO'
]

# Configuración de SPE
SPE_CONFIG = {
    'spreadsheet_id': st.secrets["google"]["spreadsheet_id"] if "google" in st.secrets else None,
    'range_name': st.secrets["google"]["range_name"] if "google" in st.secrets else None,
    'local_file': 'descargas/SPE/MATRIZ.xlsx'
}

# Configuración de seguridad
try:
    ADMIN_PASSWORD = st.secrets["passwords"]["admin_password"]
except:
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'default_password')