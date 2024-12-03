import os

# Rutas base
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CREDENTIALS_DIR = os.path.join(BASE_DIR, 'credentials')
GOOGLE_CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, 'migra2024-77aaf61899d3.json')

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
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

# Otras configuraciones... 