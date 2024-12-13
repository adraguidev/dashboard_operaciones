import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS
from dotenv import load_dotenv
import logging
import time

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
                connectTimeoutMS=5000,
                socketTimeoutMS=10000,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=10,
                minPoolSize=5,
                maxIdleTimeMS=45000,
                waitQueueTimeoutMS=5000,
                appName='MigracionesApp',
                compressors=['zlib'],
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
            raise

    def _get_collection_last_update(_self, collection_name: str) -> datetime:
        """Obtiene la última fecha de actualización de una colección."""
        try:
            latest_doc = _self.migraciones_db[collection_name].find_one(
                {},
                sort=[('FechaActualizacion', -1)],
                projection={'FechaActualizacion': 1}
            )
            return latest_doc.get('FechaActualizacion') if latest_doc else None
        except Exception as e:
            print(f"Error al obtener última actualización: {str(e)}")
            return None

    @st.cache_data(ttl=None)  # Sin TTL, el cache se limpiará manualmente
    def load_module_data(_self, module_name: str, last_update: datetime = None) -> pd.DataFrame:
        """
        Carga datos consolidados desde migraciones_db.
        El parámetro last_update se usa como hash key para invalidar el cache.
        """
        try:
            # SPE siempre se carga fresco (sin cache)
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            print(f"Cargando datos para módulo: {module_name}")
            start_time = time.time()

            # Procesamiento especial para CCM-LEY
            if module_name == 'CCM-LEY':
                ccm_data = _self.load_module_data('CCM')
                ccm_esp_data = _self.load_module_data('CCM-ESP')
                
                if ccm_data is not None and ccm_esp_data is not None:
                    data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
                    if 'TipoTramite' in data.columns:
                        data = data[data['TipoTramite'] == 'LEY'].copy()
                    return data
                else:
                    st.error("No se pudieron cargar los datos necesarios para CCM-LEY")
                    return None

            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            # Obtener datos con proyección optimizada
            projection = {
                "NumeroTramite": 1,
                "EVALASIGN": 1,
                "Evaluado": 1,
                "ESTADO": 1,
                "UltimaEtapa": 1,
                "FechaExpendiente": 1,
                "FechaPre": 1,
                "FechaTramite": 1,
                "FechaAsignacion": 1,
                "FechaEtapaAprobacionMasivaFin": 1,
                "FECHA DE TRABAJO": 1,
                "TipoTramite": 1,
                "Proceso": 1,
                "Etapa": 1,
                "Anio": 1,
                "Mes": 1,
                "_id": 0
            }
            
            collection = _self.migraciones_db[collection_name]
            cursor = collection.find({}, projection)
            data = pd.DataFrame(list(cursor))

            if data.empty:
                return None

            # Convertir fechas
            for col in DATE_COLUMNS:
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce')

            print(f"Tiempo de carga para {module_name}: {time.time() - start_time:.2f} segundos")
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