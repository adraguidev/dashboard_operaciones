import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS

class DataLoader:
    def __init__(_self):
        """Inicializa la conexión a MongoDB usando los secrets de Streamlit."""
        try:
            _self.client = MongoClient(st.secrets["connections"]["mongodb"]["uri"])
            _self.db = _self.client['migraciones_db']
        except Exception as e:
            st.error(f"Error al conectar con MongoDB: {str(e)}")
            raise

    @st.cache_data(ttl=3600)  # Cache por 1 hora
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos de cualquier módulo de manera unificada."""
        try:
            # SPE usa Google Sheets
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            # Obtener datos de MongoDB
            collection = _self.db[collection_name]
            cursor = collection.find({}, {'_id': 0})
            data = pd.DataFrame(list(cursor))

            if data.empty:
                return None

            # Convertir columnas de fecha - Modificado para manejar múltiples formatos
            date_columns = [
                'FechaExpendiente', 'FechaEtapaAprobacionMasivaFin', 
                'FechaPre', 'FechaTramite', 'FechaAsignacion',
                'FECHA DE TRABAJO'
            ]
            
            for col in date_columns:
                if col in data.columns:
                    try:
                        # Primero intentar con formato específico dd/mm/yyyy
                        data[col] = pd.to_datetime(
                            data[col], 
                            format='%d/%m/%Y',
                            errors='coerce'
                        )
                    except:
                        try:
                            # Si falla, intentar con dayfirst=True para formatos variados
                            data[col] = pd.to_datetime(
                                data[col], 
                                dayfirst=True,
                                errors='coerce'
                            )
                        except:
                            pass

                    # Si hay valores nulos, intentar otros formatos comunes
                    if data[col].isna().any():
                        mask = data[col].isna()
                        try:
                            # Intentar formato yyyy-mm-dd
                            temp_dates = pd.to_datetime(
                                data.loc[mask, col],
                                format='%Y-%m-%d',
                                errors='coerce'
                            )
                            data.loc[mask, col] = temp_dates
                        except:
                            pass

                    # Asegurar que no tiene timezone
                    if data[col].dtype == 'datetime64[ns]' and data[col].dt.tz is not None:
                        data[col] = data[col].dt.tz_localize(None)

            # Procesar datos específicos del módulo
            if module_name == 'CCM-LEY':
                data = _self._process_ccm_ley_data(data)
            
            return data

        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")
            return None

    @st.cache_data(ttl=3600)
    def get_latest_update(_self, module_name: str) -> datetime:
        """Obtiene la fecha de la última actualización de un módulo."""
        try:
            collection_name = f"consolidado_{module_name.lower()}_historical"
            historical_collection = _self.db[collection_name]
            latest = historical_collection.find_one(
                {},
                sort=[('metadata.fecha_actualizacion', -1)],
                projection={'metadata.fecha_actualizacion': 1}
            )
            return latest['metadata']['fecha_actualizacion'] if latest else None
        except Exception as e:
            st.error(f"Error al obtener última actualización: {str(e)}")
            return None

    def _process_ccm_ley_data(_self, data: pd.DataFrame) -> pd.DataFrame:
        """Procesa datos específicos para CCM-LEY."""
        return data[data['TipoTramite'] == 'LEY'].copy()

    def _load_spe_from_sheets(_self):
        """Carga datos de SPE desde Google Sheets."""
        try:
            folder = "descargas/SPE"
            file_path = os.path.join(folder, "MATRIZ.xlsx")
            if os.path.exists(file_path):
                data = pd.read_excel(file_path)
                return data
            return None
        except Exception as e:
            st.error(f"Error al cargar datos de SPE: {str(e)}")
            return None