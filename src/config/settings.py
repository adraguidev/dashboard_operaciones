import os
from dataclasses import dataclass, field
from typing import Dict, List
import streamlit as st
from functools import lru_cache
from typing import Optional

@dataclass
class ModuleConfig:
    """Configuración unificada de módulos"""
    name: str
    display_name: str
    icon: str
    folder: str
    collection: str
    inactive_evaluators: List[str]
    vulnerabilidad_evaluators: List[str] = field(default_factory=list)

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
        display_name='Calidad Migratoria',
        icon='📋',
        folder='descargas/CCM',
        collection='consolidado_ccm',
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
        ],
        vulnerabilidad_evaluators=[
            "Quispe Orosco, Karina Wendy",
            "Miranda Avila, Marco Antonio",
            "Aponte Sanchez, Paola Lita",
            "Orcada Herrera, Javier Eduardo",
            "Gomez Vera, Marcos Alberto"
        ]
    ),
    'PRR': ModuleConfig(
        name='PRR',
        display_name='Prórroga de Residencia',
        icon='📈',
        folder='descargas/PRR',
        collection='consolidado_prr',
        inactive_evaluators=[]
    ),
    'CCM-ESP': ModuleConfig(
        name='CCM-ESP',
        display_name='Calidad Migratoria Especial',
        icon='📉',
        folder='descargas/CCM-ESP',
        collection='consolidado_ccm_esp',
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
        ],
        vulnerabilidad_evaluators=[
            "Quispe Orosco, Karina Wendy",
            "Miranda Avila, Marco Antonio",
            "Aponte Sanchez, Paola Lita",
            "Orcada Herrera, Javier Eduardo",
            "Gomez Vera, Marcos Alberto"
        ]
    ),
    'CCM-LEY': ModuleConfig(
        name='CCM-LEY',
        display_name='Calidad Migratoria Ley',
        icon='📋',
        folder='descargas/CCM-LEY',
        collection='consolidado_ccm',
        inactive_evaluators=[]
    ),
    'SOL': ModuleConfig(
        name='SOL',
        display_name='Solicitudes',
        icon='📂',
        folder='descargas/SOL',
        collection='consolidado_sol',
        inactive_evaluators=[]
    ),
    'SPE': ModuleConfig(
        name='SPE',
        display_name='Sistema de Permisos Especiales',
        icon='💼',
        folder='descargas/SPE',
        collection='consolidado_spe',
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
@lru_cache()
def get_admin_password() -> str:
    """Obtiene la contraseña de administrador de manera segura"""
    password = st.secrets.get("admin", {}).get("password") or os.getenv('ADMIN_PASSWORD')
    if not password:
        raise ValueError("No se ha configurado la contraseña de administrador")
    return password

@dataclass
class MongoDBConfig:
    """Configuración de MongoDB"""
    uri: str
    database: str
    collections: Dict[str, str]
    
    @classmethod
    def from_env(cls) -> 'MongoDBConfig':
        """Carga configuración desde variables de entorno"""
        uri = os.getenv('MONGODB_URI')
        if not uri:
            raise ValueError("MONGODB_URI no está configurado")
        return cls(
            uri=uri,
            database=os.getenv('MONGODB_DATABASE', 'migraciones_db'),
            collections=MONGODB_COLLECTIONS
        )