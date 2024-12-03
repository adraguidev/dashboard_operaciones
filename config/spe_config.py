import os

# Obtener la ruta base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SPE_SETTINGS = {
    'SPREADSHEET_ID': '1QbBSDyxjTfldzEH9Y4wK09x9hknMXfe7svS4hOU4EDw',
    'WORKSHEET_NAME': 'MATRIZ',
    'CREDENTIALS_PATH': os.path.join(BASE_DIR, 'credentials', 'migra2024-77aaf61899d3.json')
} 