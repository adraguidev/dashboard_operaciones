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
                    # Primero intentar convertir desde el formato guardado
                    try:
                        # Convertir a datetime sin timezone
                        data[col] = pd.to_datetime(data[col], errors='coerce')
                        if data[col].dt.tz is not None:
                            data[col] = data[col].dt.tz_localize(None)
                    except:
                        pass

                    # Si hay valores nulos, intentar diferentes formatos
                    if data[col].isna().any():
                        # Intentar formatos comunes
                        formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']
                        for fmt in formats:
                            try:
                                mask = data[col].isna()
                                temp_dates = pd.to_datetime(
                                    data.loc[mask, col], 
                                    format=fmt, 
                                    errors='coerce'
                                )
                                # Asegurar que no tiene timezone
                                if temp_dates.dt.tz is not None:
                                    temp_dates = temp_dates.dt.tz_localize(None)
                                data.loc[mask, col] = temp_dates
                            except:
                                continue

                # Asegurar que todas las fechas son timezone-naive
                if col in data.columns and not data[col].empty:
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