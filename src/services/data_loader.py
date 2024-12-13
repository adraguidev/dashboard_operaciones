import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Obtener las variables de entorno
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')

class DataLoader:
    def __init__(_self):
        """Inicializa las conexiones a MongoDB usando los secrets de Streamlit o variables de entorno."""
        try:
            logger.info("Iniciando conexión a MongoDB...")
            # Primero intentar obtener la URI desde secrets de Streamlit
            try:
                mongo_uri = st.secrets["connections"]["mongodb"]["uri"]
                logger.info("Usando URI de MongoDB desde Streamlit secrets")
            except:
                # Si no está en secrets, usar variables de entorno
                load_dotenv()
                mongo_uri = os.getenv('MONGODB_URI')
                if not mongo_uri:
                    raise ValueError("No se encontró la URI de MongoDB en secrets ni en variables de entorno")
                logger.info("Usando URI de MongoDB desde variables de entorno")

            _self.client = MongoClient(
                mongo_uri,
                connectTimeoutMS=30000,
                socketTimeoutMS=None,
                serverSelectionTimeoutMS=30000,
                retryWrites=True,
                retryReads=True
            )
            
            # Base de datos para datos consolidados
            _self.migraciones_db = _self.client['migraciones_db']
            # Base de datos para rankings
            _self.expedientes_db = _self.client['expedientes_db']
            
            # Verificar conexiones con timeout
            _self.migraciones_db.command('ping', maxTimeMS=5000)
            _self.expedientes_db.command('ping', maxTimeMS=5000)
            
            logger.info("Conexión exitosa a MongoDB")
        except Exception as e:
            logger.error(f"Error detallado de conexión: {str(e)}")
            st.error(f"Error al conectar con MongoDB: {str(e)}")
            st.info("Verificando configuración...")
            st.info("1. ¿La URI de MongoDB está configurada correctamente?")
            st.info("2. ¿Tu IP está en la lista blanca de MongoDB Atlas?")
            st.info("3. ¿Las credenciales son correctas?")
            raise

    @st.cache_data(ttl=3600)
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos consolidados desde migraciones_db."""
        try:
            # SPE usa Google Sheets
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            # Procesamiento especial para CCM-LEY
            if module_name == 'CCM-LEY':
                # Cargar datos de CCM y CCM-ESP
                ccm_data = _self.load_module_data('CCM')
                ccm_esp_data = _self.load_module_data('CCM-ESP')
                
                if ccm_data is not None and ccm_esp_data is not None:
                    # Filtrar CCM-LEY: registros de CCM que no están en CCM-ESP
                    data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
                    
                    # Verificar si existe la columna TipoTramite y filtrar
                    if 'TipoTramite' in data.columns:
                        data = data[data['TipoTramite'] == 'LEY'].copy()
                    return data
                else:
                    st.error("No se pudieron cargar los datos necesarios para CCM-LEY")
                    return None

            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            # Obtener datos de migraciones_db
            collection = _self.migraciones_db[collection_name]
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