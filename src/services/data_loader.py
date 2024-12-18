import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import (
    MONGODB_COLLECTIONS, 
    DATE_COLUMNS, 
    REDIS_CONNECTION,
    REDIS_MEMORY_LIMIT,
    CACHE_TTL
)
from dotenv import load_dotenv
import logging
import time
import redis
import pickle
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class DataLoader:
    def __init__(_self):
        """Inicializa las conexiones a MongoDB y Redis."""
        try:
            logger.info("Iniciando conexiones...")
            
            # Configuración de Redis
            _self.redis_client = redis.Redis(
                **REDIS_CONNECTION,
                socket_connect_timeout=5
            )
            
            # Verificar conexión a Redis
            _self.redis_client.ping()
            logger.info("Conexión a Redis establecida")
            
            # Resto de la inicialización de MongoDB...
            try:
                mongo_uri = st.secrets["connections"]["mongodb"]["uri"]
                logger.info("Usando URI de MongoDB desde Streamlit secrets")
            except:
                load_dotenv()
                mongo_uri = os.getenv('MONGODB_URI')
                if not mongo_uri:
                    raise ValueError("No se encontró la URI de MongoDB")
                logger.info("Usando URI de MongoDB desde variables de entorno")

            # Resto del código de inicialización de MongoDB...
            
            logger.info("Todas las conexiones establecidas correctamente")
        except redis.ConnectionError as e:
            logger.error(f"Error al conectar con Redis: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error en inicialización: {str(e)}")
            raise

    def _get_cache_key(_self, module_name: str, operation: str = 'data') -> str:
        """Genera una clave única para el cache."""
        return f"migraciones:{module_name}:{operation}"

    def _get_cache_size(_self) -> float:
        """Obtiene el tamaño actual del cache en MB."""
        try:
            info = _self.redis_client.info(section='memory')
            return info['used_memory'] / 1024 / 1024
        except:
            return 0

    def _cache_data(_self, module_name: str, data: pd.DataFrame) -> bool:
        """Almacena datos en Redis con compresión."""
        try:
            cache_key = _self._get_cache_key(module_name)
            
            # Verificar espacio disponible
            current_size = _self._get_cache_size()
            if current_size > (REDIS_MEMORY_LIMIT * 0.9):  # 90% del límite
                logger.warning("Cache casi lleno, limpiando datos antiguos...")
                _self.redis_client.flushdb()
            
            # Serializar DataFrame
            serialized_data = pickle.dumps(data)
            
            # Guardar en Redis con TTL
            ttl = CACHE_TTL.get(module_name, CACHE_TTL['default'])
            success = _self.redis_client.setex(cache_key, ttl, serialized_data)
            
            if success:
                # Guardar metadata del cache
                metadata = {
                    'rows': len(data),
                    'columns': list(data.columns),
                    'cached_at': datetime.now().isoformat(),
                    'ttl': ttl
                }
                metadata_key = _self._get_cache_key(module_name, 'metadata')
                _self.redis_client.setex(metadata_key, ttl, json.dumps(metadata))
                
                logger.info(f"Datos cacheados para {module_name}: {len(data)} registros")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al cachear datos: {str(e)}")
            return False

    def _get_cached_data(_self, module_name: str) -> pd.DataFrame:
        """Recupera datos cacheados de Redis."""
        try:
            cache_key = _self._get_cache_key(module_name)
            cached_data = _self.redis_client.get(cache_key)
            
            if cached_data:
                # Obtener metadata
                metadata_key = _self._get_cache_key(module_name, 'metadata')
                metadata = _self.redis_client.get(metadata_key)
                if metadata:
                    metadata = json.loads(metadata)
                    logger.info(f"Usando cache para {module_name} - {metadata['rows']} registros")
                
                return pickle.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Error al recuperar cache: {str(e)}")
            return None

    def force_data_refresh(_self, password: str) -> bool:
        """Fuerza actualización limpiando el cache."""
        if not _self.verify_password(password):
            st.error("Contraseña incorrecta")
            return False
        
        try:
            # Limpiar cache de Redis
            _self.redis_client.flushdb()
            logger.info("Cache de Redis limpiado")
            
            # Cargar datos frescos para cada módulo
            modules = ['CCM', 'CCM-ESP', 'PRR', 'SOL']
            with st.spinner("Actualizando datos..."):
                for module in modules:
                    data = _self._load_fresh_data(module)
                    if data is not None:
                        _self._cache_data(module, data)
                        
                # CCM-LEY se procesa después de CCM y CCM-ESP
                ccm_data = _self._get_cached_data('CCM')
                ccm_esp_data = _self._get_cached_data('CCM-ESP')
                if ccm_data is not None and ccm_esp_data is not None:
                    ccm_ley_data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
                    _self._cache_data('CCM-LEY', ccm_ley_data)
            
            st.success("✅ Datos actualizados y cacheados correctamente")
            return True
        except Exception as e:
            logger.error(f"Error en actualización: {str(e)}")
            st.error(f"Error al actualizar datos: {str(e)}")
            return False

    def _load_fresh_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos frescos desde MongoDB."""
        try:
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            collection = _self.migraciones_db[collection_name]
            cursor = collection.find(
                {},
                {'_id': 0},
                batch_size=5000
            ).allow_disk_use(True)

            data = pd.DataFrame(list(cursor))
            
            # Procesar fechas
            for col in DATE_COLUMNS:
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce')
            
            return data
        except Exception as e:
            logger.error(f"Error cargando datos frescos: {str(e)}")
            return None

    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos con soporte de cache Redis."""
        try:
            # SPE siempre se carga fresco
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            # Intentar obtener del cache
            cached_data = _self._get_cached_data(module_name)
            if cached_data is not None:
                return cached_data

            # Si no hay cache, cargar datos frescos
            data = _self._load_fresh_data(module_name)
            if data is not None:
                _self._cache_data(module_name, data)
            return data

        except Exception as e:
            logger.error(f"Error al cargar datos: {str(e)}")
            return None

    def setup_indexes(_self):
        """Configura índices para optimizar consultas frecuentes."""
        try:
            for collection_name in MONGODB_COLLECTIONS.values():
                collection = _self.migraciones_db[collection_name]
                # Crear índices solo si no existen
                existing_indexes = collection.index_information()
                
                # Índices necesarios para las consultas más frecuentes
                required_indexes = [
                    [("FechaExpendiente", 1)],
                    [("FechaPre", 1)],
                    [("EVALASIGN", 1)],
                    [("NumeroTramite", 1)]
                ]
                
                for index in required_indexes:
                    index_name = "_".join([f"{field}_{direction}" for field, direction in index])
                    if index_name not in existing_indexes:
                        collection.create_index(index, background=True)
                        logger.info(f"Índice {index_name} creado en {collection_name}")
                        
        except Exception as e:
            logger.error(f"Error al crear índices: {str(e)}")

    def verify_password(_self, password: str) -> bool:
        """Verifica si la contraseña proporcionada es correcta."""
        correct_password = "Ka260314!"
        return password == correct_password

    def _optimize_dtypes(_self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimiza los tipos de datos del DataFrame para reducir uso de memoria."""
        # Convertir columnas numéricas a tipos más eficientes
        for col in df.select_dtypes(include=['int64']).columns:
            if df[col].min() >= 0:  # Si son todos positivos
                if df[col].max() < 255:
                    df[col] = df[col].astype('uint8')
                elif df[col].max() < 65535:
                    df[col] = df[col].astype('uint16')
                else:
                    df[col] = df[col].astype('uint32')
            else:
                if df[col].min() > -128 and df[col].max() < 127:
                    df[col] = df[col].astype('int8')
                elif df[col].min() > -32768 and df[col].max() < 32767:
                    df[col] = df[col].astype('int16')
                else:
                    df[col] = df[col].astype('int32')

        # Optimizar columnas de texto que se repiten frecuentemente
        for col in df.select_dtypes(include=['object']).columns:
            if df[col].nunique() / len(df) < 0.5:  # Si hay muchos valores repetidos
                df[col] = pd.Categorical(df[col])

        return df

    # Método separado para SPE sin caché - siempre carga datos frescos
    def _load_spe_from_sheets(_self):
        """Carga datos de SPE desde Google Sheets. Sin caché para mantener datos frescos."""
        try:
            print("Cargando datos frescos de SPE desde archivo...")
            folder = "descargas/SPE"
            file_path = os.path.join(folder, "MATRIZ.xlsx")
            
            if not os.path.exists(file_path):
                st.error(f"No se encontró el archivo de SPE en {file_path}")
                return None
                
            data = pd.read_excel(file_path)
            if data.empty:
                st.error("El archivo de SPE está vacío")
                return None
                
            print(f"Datos frescos de SPE cargados exitosamente: {len(data)} registros")
            return data
            
        except Exception as e:
            error_msg = f"Error al cargar datos de SPE: {str(e)}"
            logger.error(error_msg)
            st.error(error_msg)
            return None

    def get_rankings_collection(_self):
        """Retorna la colección de rankings de expedientes_db."""
        return _self.expedientes_db['rankings']