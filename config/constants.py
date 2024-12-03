# Constantes para fechas
DATE_FORMAT = '%d/%m/%Y'
MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# Constantes para evaluadores vulnerables
VULNERABILIDAD_EVALUATORS = [
    "Quispe Orosco, Karina Wendy",
    "Lucero Martinez, Carlos Martin",
    "Gomez Vera, Marcos Alberto",
    "Aponte Sanchez, Paola Lita",
    "Santibañez Chafalote, Lila Mariella",
    "VULNERABILIDAD"
]

# Constantes para estados
ESTADOS = {
    'PENDIENTE': 'NO',
    'COMPLETADO': 'SI'
}

# Configuración de visualización
CHART_COLORS = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'danger': '#d62728',
    'warning': '#ffbb78'
}

# Configuración de la interfaz
UI_CONFIG = {
    'table_page_size': 10,
    'chart_height': 400,
    'sidebar_width': 300
}

# Configuración de validación
VALIDATION_THRESHOLDS = {
    'missing_dates_warning': 5,
    'invalid_dates_warning': 3,
    'data_completeness_minimum': 95
} 