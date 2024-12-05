import os

# Configuración de módulos
MODULES = {
    'CCM': 'Calidad Migratoria',
    'PRR': 'Prórroga de Residencia',
    'CCM-ESP': 'Calidad Migratoria Especial',
    'CCM-LEY': 'Calidad Migratoria Ley',
    'SOL': 'Solicitudes',
    'SPE': 'Sistema de Permisos Especiales'
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
        "VULNERABILIDAD",
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
        "VULNERABILIDAD",
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
        "VULNERABILIDAD",
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
        "VULNERABILIDAD",
        "SUSPENDIDA",
        "Quispe Orosco, Karina Wendy",
        "Gomez Vera, Marcos Alberto",
        "Lucero Martinez, Carlos Martin",
        "Aponte Sanchez, Paola Lita"
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
    'CCM': 'Calidad Migratoria',
    'PRR': 'Prórroga de Residencia',
    'CCM-ESP': 'Calidad Migratoria Especial',
    'CCM-LEY': 'Calidad Migratoria Ley',
    'SOL': 'Solicitudes',
    'SPE': 'Sistema de Permisos Especiales'
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