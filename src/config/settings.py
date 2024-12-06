import os
from dataclasses import dataclass
from typing import Dict, List

# Configuración de módulos
@dataclass
class ModuleConfig:
    name: str
    icon: str
    folder: str
    inactive_evaluators: List[str]

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
        icon='📈',
        folder='descargas/PRR',
        inactive_evaluators=[]
    ),
    'CCM-ESP': ModuleConfig(
        name='CCM-ESP',
        icon='📉',
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
        icon='📋',
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
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

# Agregar al archivo de configuración
ADMIN_PASSWORD = "Ka260314!"  # Idealmente esto debería estar en st.secrets

# Configuración de colecciones MongoDB
MONGODB_COLLECTIONS = {
    'CCM': 'consolidado_ccm',
    'PRR': 'consolidado_prr',
    'CCM-ESP': 'consolidado_ccm_esp',
    'CCM-LEY': 'consolidado_ccm',  # Usa la misma colección que CCM
    'SOL': 'consolidado_sol',
    'SPE': 'consolidado_spe'
}

# Otras configuraciones... 