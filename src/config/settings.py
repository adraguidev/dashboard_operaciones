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
        inactive_evaluators=[...]
    ),
    'PRR': ModuleConfig(
        name='PRR',
        icon='📈',
        folder='descargas/PRR',
        inactive_evaluators=[...]
    ),
    'CCM-ESP': ModuleConfig(
        name='CCM-ESP',
        icon='📉',
        folder='descargas/CCM-ESP',
        inactive_evaluators=[...]
    ),
    'CCM-LEY': ModuleConfig(
        name='CCM-LEY',
        icon='📋',
        folder='descargas/CCM-LEY',
        inactive_evaluators=[...]
    ),
    'SOL': ModuleConfig(
        name='SOL',
        icon='📂',
        folder='descargas/SOL',
        inactive_evaluators=[...]
    ),
    'SPE': ModuleConfig(
        name='SPE',
        icon='💼',
        folder='descargas/SPE',
        inactive_evaluators=[...]
    )
}

# Configuración de Google Sheets
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

# Otras configuraciones... 