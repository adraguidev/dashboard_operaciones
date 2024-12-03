import os

# Configuración general
MODULES = {
    'CCM': '📊 CCM',
    'PRR': '📈 PRR',
    'CCM-ESP': '📉 CCM-ESP',
    'CCM-LEY': '📋 CCM-LEY', 
    'SOL': '📂 SOL',
    'SPE': '📂 SPE'
}

# Evaluadores inactivos por módulo
INACTIVE_EVALUATORS = {
    "CCM": [
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
    "PRR": [
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
        "VULNERABILIDAD",
        "SUSPENDIDA",
        "Quispe Orosco, Karina Wendy",
        "Gomez Vera, Marcos Alberto",
        "Lucero Martinez, Carlos Martin",
        "Aponte Sanchez, Paola Lita"
    ]
}

# Configuración de MongoDB
MONGODB_CONFIG = {
    "database": "expedientes_db",
    "collection": "rankings",
    "timeout_ms": 5000,  # Timeout para operaciones de MongoDB
    "retry_writes": True,
    "max_pool_size": 50
}

# Configuración de carpetas
BASE_FOLDER = 'descargas'
MODULE_FOLDERS = {
    'CCM': os.path.join(BASE_FOLDER, 'CCM'),
    'PRR': os.path.join(BASE_FOLDER, 'PRR'),
    'CCM-ESP': os.path.join(BASE_FOLDER, 'CCM-ESP'),
    'CCM-LEY': os.path.join(BASE_FOLDER, 'CCM-LEY'),
    'SOL': os.path.join(BASE_FOLDER, 'SOL'),
    'SPE': os.path.join(BASE_FOLDER, 'SPE')
}

# Configuración de manejo de errores
ERROR_CONFIG = {
    "max_retries": 3,
    "retry_delay_seconds": 1,
    "log_errors": True
}

# Asegurar que las carpetas existan
def ensure_folders_exist():
    """Crear las carpetas si no existen."""
    if not os.path.exists(BASE_FOLDER):
        os.makedirs(BASE_FOLDER)
    
    for folder in MODULE_FOLDERS.values():
        if not os.path.exists(folder):
            os.makedirs(folder)

# Crear carpetas al importar el módulo
ensure_folders_exist() 