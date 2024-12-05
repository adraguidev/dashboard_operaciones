import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os

class DataLoader:
    @st.cache_resource
    def __init__(self):
        """Inicializa la conexión a MongoDB usando los secrets de Streamlit."""
        self.client = MongoClient(st.secrets["connections"]["mongodb"]["uri"])
        self.db = self.client['migraciones_db']

    def load_module_data(self, module_name: str) -> pd.DataFrame:
        """Carga datos de cualquier módulo de manera unificada."""
        try:
            # SPE usa Google Sheets
            if module_name == 'SPE':
                return self._load_spe_from_sheets()
            
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            # Obtener datos de MongoDB
            collection = self.db[collection_name]
            cursor = collection.find({}, {'_id': 0})  # Excluir el _id de MongoDB
            data = pd.DataFrame(list(cursor))

            if data.empty:
                return None

            # Convertir columnas de fecha
            for col in DATE_COLUMNS:
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col], errors='coerce')

            # Procesar datos específicos del módulo
            if module_name == 'CCM-LEY':
                data = self._process_ccm_ley_data(data)
            
            return data

        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")
            return None

    def _validate_data(self, data: pd.DataFrame, module_name: str):
        """Valida la integridad de los datos y muestra advertencias."""
        # Verificar fechas faltantes
        date_columns = data.select_dtypes(include=['datetime64']).columns
        missing_dates = data[date_columns].isna().sum().sum()
        if missing_dates > 0:
            st.warning(f"Hay {missing_dates} registros con fechas faltantes en {module_name}")

        # Verificar campos requeridos según el módulo
        required_columns = {
            'CCM': ['NumeroTramite', 'EstadoTramite'],
            'PRR': ['NumeroTramite', 'EstadoTramite'],
            'CCM-ESP': ['NumeroTramite', 'EstadoTramite'],
            'SOL': ['NumeroTramite', 'EstadoTramite']
        }
        
        if module_name in required_columns:
            missing_cols = [col for col in required_columns[module_name] 
                          if col not in data.columns]
            if missing_cols:
                st.error(f"Faltan columnas requeridas en {module_name}: {missing_cols}")

    def _process_ccm_ley_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Procesa datos específicos para CCM-LEY."""
        # Filtrar solo registros relevantes para CCM-LEY
        return data[data['TipoTramite'] == 'LEY'].copy()

    def _process_spe_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Procesa datos específicos para SPE."""
        # Implementar lógica específica para SPE si es necesaria
        return data

    def get_latest_update(self, module_name: str) -> datetime:
        """Obtiene la fecha de la última actualización de un módulo."""
        collection_name = f"consolidado_{module_name.lower()}_historical"
        historical_collection = self.db[collection_name]
        latest = historical_collection.find_one(
            {},
            sort=[('metadata.fecha_actualizacion', -1)],
            projection={'metadata.fecha_actualizacion': 1}
        )
        return latest['metadata']['fecha_actualizacion'] if latest else None

    def _load_spe_from_sheets(self):
        """Carga datos de SPE desde Google Sheets."""
        try:
            folder = "descargas/SPE"
            file_path = os.path.join(folder, "MATRIZ.xlsx")
            if os.path.exists(file_path):
                data = pd.read_excel(file_path)
                return self._process_spe_data(data)
            return None
        except Exception as e:
            st.error(f"Error al cargar datos de SPE: {str(e)}")
            return None