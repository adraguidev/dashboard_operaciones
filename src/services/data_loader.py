import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS
from dotenv import load_dotenv
import logging
import time
import hashlib
from functools import lru_cache
import gc

# Configuración de logging mejorada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno una sola vez
load_dotenv()

class DataLoader:
    _instance = None
    _is_initialized = False

    def __new__(cls):
        """Implementar patrón Singleton para evitar múltiples conexiones."""
        if cls._instance is None:
            cls._instance = super(DataLoader, cls).__new__(cls)
        return cls._instance

    def __init__(_self):
        """Inicializa las conexiones a MongoDB usando los secrets de Streamlit o variables de entorno."""
        if DataLoader._is_initialized:
            return
        
        try:
            logger.info("Iniciando conexión a MongoDB...")
            mongo_uri = _self._get_mongo_uri()
            _self.client = _self._create_mongo_client(mongo_uri)
            
            # Inicializar bases de datos
            _self.migraciones_db = _self.client['migraciones_db']
            _self.expedientes_db = _self.client['expedientes_db']
            
            # Verificar conexiones
            _self._verify_connections()
            
            # Cache en memoria para optimizar consultas frecuentes
            _self._projection_cache = {}
            _self._collection_stats = {}
            
            DataLoader._is_initialized = True
            logger.info("Conexión exitosa a MongoDB")
        except Exception as e:
            logger.error(f"Error detallado de conexión: {str(e)}")
            raise

    @staticmethod
    def _get_mongo_uri():
        """Obtiene la URI de MongoDB de manera segura."""
        try:
            return st.secrets["connections"]["mongodb"]["uri"]
        except:
            uri = os.getenv('MONGODB_URI')
            if not uri:
                raise ValueError("No se encontró la URI de MongoDB")
            return uri

    @staticmethod
    def _create_mongo_client(mongo_uri):
        """Crea y configura el cliente de MongoDB con opciones optimizadas."""
        return MongoClient(
            mongo_uri,
            connectTimeoutMS=5000,
            socketTimeoutMS=10000,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10,  # Aumentado para mejor concurrencia
            minPoolSize=5,   # Aumentado para mantener conexiones activas
            maxIdleTimeMS=300000,
            waitQueueTimeoutMS=5000,
            appName='MigracionesApp',
            compressors=['zlib'],
            retryWrites=True,
            retryReads=True,
            w='majority',  # Garantizar consistencia
            readPreference='primaryPreferred'  # Optimizar lecturas
        )

    def _verify_connections(_self):
        """Verifica las conexiones a las bases de datos."""
        for db in [_self.migraciones_db, _self.expedientes_db]:
            try:
                db.command('ping', maxTimeMS=5000)
            except Exception as e:
                logger.error(f"Error al verificar conexión: {str(e)}")
                raise

    @lru_cache(maxsize=32)
    def _get_optimized_projection(_self, module_name: str) -> dict:
        """Cache de proyecciones por módulo."""
        if module_name not in _self._projection_cache:
            _self._projection_cache[module_name] = {
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
        return _self._projection_cache[module_name]

    def _optimize_dataframe(_self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimiza el uso de memoria del DataFrame."""
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = pd.Categorical(df[col])
            elif df[col].dtype == 'float64' and df[col].isna().sum() == 0:
                df[col] = df[col].astype('float32')
        return df

    @st.cache_data(ttl=None, show_spinner=False)  # Cache permanente
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos consolidados desde migraciones_db con optimizaciones."""
        try:
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            start_time = time.time()
            logger.info(f"Cargando datos para módulo: {module_name}")

            # Manejo especial para CCM-LEY
            if module_name == 'CCM-LEY':
                return _self._load_ccm_ley_data()

            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            # Obtener datos con proyección optimizada
            collection = _self.migraciones_db[collection_name]
            projection = _self._get_optimized_projection(module_name)
            
            # Usar cursor con batch_size optimizado
            cursor = collection.find({}, projection).batch_size(1000)
            data = pd.DataFrame(list(cursor))

            if data.empty:
                return None

            # Optimizar tipos de datos y memoria
            data = _self._optimize_dataframe(data)

            # Convertir fechas eficientemente
            _self._convert_dates(data)

            # Limpiar memoria
            gc.collect()

            logger.info(f"Tiempo de carga para {module_name}: {time.time() - start_time:.2f} segundos")
            return data

        except Exception as e:
            logger.error(f"Error al cargar datos: {str(e)}")
            return None

    def _convert_dates(_self, df: pd.DataFrame) -> None:
        """Convierte columnas de fecha eficientemente."""
        for col in DATE_COLUMNS:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', errors='coerce')

    def _load_ccm_ley_data(_self) -> pd.DataFrame:
        """Carga y procesa datos específicos para CCM-LEY."""
        ccm_data = _self.load_module_data('CCM')
        ccm_esp_data = _self.load_module_data('CCM-ESP')
        
        if ccm_data is not None and ccm_esp_data is not None:
            # Usar merge en lugar de isin para mejor rendimiento
            data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
            if 'TipoTramite' in data.columns:
                data = data[data['TipoTramite'] == 'LEY'].copy()
            return _self._optimize_dataframe(data)
        return None

    @st.cache_data(ttl=None, show_spinner=False)
    def _load_spe_from_sheets(_self) -> pd.DataFrame:
        """Carga datos de SPE desde Excel con optimizaciones."""
        try:
            file_path = os.path.join("descargas/SPE", "MATRIZ.xlsx")
            if os.path.exists(file_path):
                # Usar dtype_backend='pyarrow' para mejor rendimiento
                data = pd.read_excel(
                    file_path,
                    engine='openpyxl',
                    dtype_backend='pyarrow'
                )
                return _self._optimize_dataframe(data)
            return None
        except Exception as e:
            logger.error(f"Error al cargar datos de SPE: {str(e)}")
            return None

    def get_rankings_collection(_self):
        """Retorna la colección de rankings."""
        return _self.expedientes_db['rankings']

    def __del__(_self):
        """Limpieza de recursos al destruir la instancia."""
        try:
            if hasattr(_self, 'client'):
                _self.client.close()
        except:
            pass