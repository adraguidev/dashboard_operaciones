import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener las variables de entorno
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')

class DataLoader:
    def __init__(_self):
        """Inicializa las conexiones a MongoDB usando los secrets de Streamlit."""
        try:
            # Agregar timeout y retry options para conexión más robusta
            _self.client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                retryWrites=True
            )
            _self.migraciones_db = _self.client['migraciones_db']
            _self.expedientes_db = _self.client['expedientes_db']
            
            # Verificar conexiones con timeout
            _self.migraciones_db.command('ping', maxTimeMS=5000)
            _self.expedientes_db.command('ping', maxTimeMS=5000)
        except Exception as e:
            st.error(f"Error al conectar con MongoDB: {str(e)}")
            raise

    @st.cache_data(ttl=3600)
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos consolidados desde migraciones_db."""
        try:
            # Agregar manejo de memoria para datasets grandes
            with st.spinner(f'Cargando datos de {module_name}...'):
                # SPE usa Google Sheets
                if module_name == 'SPE':
                    return _self._load_spe_from_sheets()
                
                collection_name = MONGODB_COLLECTIONS.get(module_name)
                if not collection_name:
                    raise ValueError(f"Módulo no reconocido: {module_name}")

                # Obtener datos con timeout y manejo de errores mejorado
                collection = _self.migraciones_db[collection_name]
                try:
                    cursor = collection.find(
                        {}, 
                        {'_id': 0},
                        no_cursor_timeout=True,
                        batch_size=1000
                    )
                    data = pd.DataFrame(list(cursor))
                finally:
                    if 'cursor' in locals():
                        cursor.close()

                if data.empty:
                    st.warning(f"No se encontraron datos para el módulo {module_name}")
                    return None

                # Optimizar procesamiento de fechas
                data = _self._process_dates(data)
                
                # Procesar datos específicos del módulo
                if module_name == 'CCM-LEY':
                    data = _self._process_ccm_ley_data(data)
                
                return data

        except Exception as e:
            st.error(f"Error al cargar datos de {module_name}: {str(e)}")
            print(f"Error detallado en load_module_data: {str(e)}")
            return None

    @st.cache_data(ttl=3600)
    def get_latest_update(_self, module_name: str) -> datetime:
        """Obtiene la fecha de la última actualización de un módulo."""
        try:
            collection_name = f"consolidado_{module_name.lower()}_historical"
            historical_collection = _self.expedientes_db[collection_name]
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

    def get_rankings_collection(_self):
        """Retorna la colección de rankings de expedientes_db."""
        return _self.expedientes_db['rankings']

    def _process_dates(_self, data: pd.DataFrame) -> pd.DataFrame:
        """Procesa las columnas de fecha de manera más eficiente."""
        date_columns = [
            'FechaExpendiente', 'FechaEtapaAprobacionMasivaFin', 
            'FechaPre', 'FechaTramite', 'FechaAsignacion',
            'FECHA DE TRABAJO'
        ]
        
        for col in date_columns:
            if col in data.columns:
                try:
                    # Convertir a datetime usando coerce para manejar errores silenciosamente
                    data[col] = pd.to_datetime(
                        data[col],
                        format='mixed',
                        dayfirst=True,
                        errors='coerce'
                    )
                    
                    # Limpiar timezone si existe
                    if data[col].dtype == 'datetime64[ns]' and hasattr(data[col].dt, 'tz') and data[col].dt.tz is not None:
                        data[col] = data[col].dt.tz_localize(None)
                except Exception as e:
                    print(f"Error procesando columna {col}: {str(e)}")
                    continue
                    
        return data