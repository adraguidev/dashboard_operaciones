import os

# Configuración de módulos
MODULES = {
    'CCM': '📊 CCM',
    'PRR': '📈 PRR',
    'CCM-ESP': '📉 CCM-ESP',
    'CCM-LEY': '📋 CCM-LEY',
    'SOL': '📂 SOL',
    'SPE': '📂 SPE'
}

# Configuración de Google Sheets
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
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

# Lista de evaluadores inactivos
INACTIVE_EVALUATORS = ['GRODRIGUEZ']  # Lista de evaluadores que no deben aparecer en los reportes

# Configuración de MongoDB
MONGODB_CONFIG = {
    'database': 'expedientes_db',
    'collections': {
        'rankings': 'rankings',
        'historico': 'historico'
    }
}