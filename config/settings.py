import os
import streamlit as st

# Configuración de módulos
MODULES = {
    'CCM': '📋 CCM',           # Calidad Migratoria
    'PRR': '🔄 PRR',           # Prórroga de Residencia
    'CCM-ESP': '⭐ CCM-ESP',    # Calidad Migratoria Especial
    'CCM-LEY': '⚖️ CCM-LEY',   # Calidad Migratoria Ley
    'SOL': '📝 SOL',           # Solicitudes
    'SPE': '🌟 SPE'            # Sistema de Permisos Especiales
}

# Configuración de Google Sheets
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Configuración de carpetas de módulos
MODULE_FOLDERS = {
    'CCM': 'descargas/CCM',
    'PRR': 'descargas/PRR',
    'CCM-ESP': 'descargas/CCM-ESP',
    'CCM-LEY': 'descargas/CCM-LEY',
    'SOL': 'descargas/SOL',
    'SPE': 'descargas/SPE'
}

# Lista de evaluadores inactivos por módulo
INACTIVE_EVALUATORS = {
    'CCM': [
        "Mauricio Romero, Hugo",
        "Ugarte Sánchez, Paulo César",
        "Santibañez Chafalote, Lila Mariella",
        "Quispe Orosco, Karina Wendy",
        "Miranda Avila, Marco Antonio",
        "Aponte Sanchez, Paola Lita",
        "Orcada Herrera, Javier Eduardo",
        "Gomez Vera, Marcos Alberto",
        "SUSPENDIDA"
    ],
    'CCM-ESP': [
        "Mauricio Romero, Hugo",
        "Ugarte Sánchez, Paulo César",
        "Santibañez Chafalote, Lila Mariella",
        "Quispe Orosco, Karina Wendy",
        "Miranda Avila, Marco Antonio",
        "Aponte Sanchez, Paola Lita",
        "Orcada Herrera, Javier Eduardo",
        "Gomez Vera, Marcos Alberto",
        "SUSPENDIDA"
    ],
    'CCM-LEY': [
        "Mauricio Romero, Hugo",
        "Ugarte Sánchez, Paulo César",
        "Santibañez Chafalote, Lila Mariella",
        "Quispe Orosco, Karina Wendy",
        "Miranda Avila, Marco Antonio",
        "Aponte Sanchez, Paola Lita",
        "Orcada Herrera, Javier Eduardo",
        "Gomez Vera, Marcos Alberto",
        "SUSPENDIDA"
    ],
    'PRR': [
        "Pozo Ferro, Sonia Leonor",
        "Bautista Lopez, Diana Carolina",
        "Infantes Panduro, Jheyson",
        "Vizcardo Ordoñez, Fiorella Carola",
        "Ponce Malpartida, Miguel",
        "Valdez Gallo, Cynthia Andrea",
        "Hurtado Lago Briyan Deivi",
        "Diaz Amaya, Esthefany Lisset",
        "Santibañez Chafalote, Lila Mariella",
        "Pumallanque Ramirez, Mariela",
        "Valera Gaviria, Jessica Valeria",
        "Vásquez Fernandez, Anthony Piere",
        "SUSPENDIDA",
        "Quispe Orosco, Karina Wendy",
        "Gomez Vera, Marcos Alberto",
        "Lucero Martinez, Carlos Martin",
        "Aponte Sanchez, Paola Lita"
    ],
    'SOL': [],
    'SPE': []
}

# Lista de evaluadores de vulnerabilidad por módulo
VULNERABILIDAD_EVALUATORS = {
    'CCM': [
        "Quispe Orosco, Karina Wendy",
        "Lucero Martinez, Carlos Martin",
        "Gomez Vera, Marcos Alberto",
        "Aponte Sanchez, Paola Lita",
        "Santibañez Chafalote, Lila Mariella",
        "VULNERABILIDAD"
    ],
    'CCM-ESP': [
        "Quispe Orosco, Karina Wendy",
        "Lucero Martinez, Carlos Martin",
        "Gomez Vera, Marcos Alberto",
        "Aponte Sanchez, Paola Lita",
        "Santibañez Chafalote, Lila Mariella",
        "VULNERABILIDAD"
    ],
    'CCM-LEY': [
        "Quispe Orosco, Karina Wendy",
        "Lucero Martinez, Carlos Martin",
        "Gomez Vera, Marcos Alberto",
        "Aponte Sanchez, Paola Lita",
        "Santibañez Chafalote, Lila Mariella",
        "VULNERABILIDAD"
    ],
    'PRR': [
        "Quispe Orosco, Karina Wendy",
        "Lucero Martinez, Carlos Martin",
        "Gomez Vera, Marcos Alberto",
        "Aponte Sanchez, Paola Lita",
        "VULNERABILIDAD"
    ],
    'SOL': [],
    'SPE': []
}

# Configuración de MongoDB
MONGODB_CONFIG = {
    'database': 'expedientes_db',
    'collections': {
        'rankings': 'rankings',
        'historico': 'historico'
    }
}

# Módulos disponibles en la aplicación
MODULES = {
    'CCM': '📋 CCM',           # Calidad Migratoria
    'PRR': '🔄 PRR',           # Prórroga de Residencia
    'CCM-ESP': '⭐ CCM-ESP',    # Calidad Migratoria Especial
    'CCM-LEY': '⚖️ CCM-LEY',   # Calidad Migratoria Ley
    'SOL': '📝 SOL',           # Solicitudes
    'SPE': '🌟 SPE'            # Sistema de Permisos Especiales
}

# Scopes para Google API
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Configuración de MongoDB
MONGODB_COLLECTIONS = {
    'CCM': 'consolidado_ccm',
    'PRR': 'consolidado_prr',
    'CCM-ESP': 'consolidado_ccm_esp',
    'CCM-LEY': 'consolidado_ccm',
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

SPE_CONFIG = {
    'spreadsheet_id': 'tu_spreadsheet_id',
    'range_name': 'tu_range',
    'local_file': 'descargas/SPE/MATRIZ.xlsx'
}

# Configuración de Redis
REDIS_CONNECTION = {
    'host': st.secrets["connections"]["redis"]["host"],
    'port': st.secrets["connections"]["redis"]["port"],
    'username': st.secrets["connections"]["redis"]["username"],
    'password': st.secrets["connections"]["redis"]["password"],
    'decode_responses': False,  # Importante: False para poder almacenar datos binarios
    'socket_timeout': 5
}

# Límites de memoria para Redis
REDIS_MEMORY_LIMIT = 25 * 1024 * 1024  # 25MB para estar seguros (el límite es 30MB)

# Configuración de TTL para el cache (en segundos)
CACHE_TTL = {
    'default': 3600,  # 1 hora por defecto
    'CCM': 3600,
    'CCM-ESP': 3600,
    'CCM-LEY': 3600,
    'PRR': 3600,
    'SOL': 3600,
    'SPE': 3600
}