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
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from multiprocessing import cpu_count
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Número de workers para procesamiento paralelo
NUM_WORKERS = min(cpu_count(), 2)  # Usar máximo 2 cores

class DataLoader:
    def __init__(_self):
        """Inicializa las conexiones a MongoDB y Redis."""
        try:
            logger.info(f"Iniciando conexiones con {NUM_WORKERS} workers...")
            
            # Configuración de Redis
            _self.redis_client = redis.Redis(
                **REDIS_CONNECTION,
                socket_connect_timeout=5
            )
            
            # Verificar conexión a Redis
            _self.redis_client.ping()
            logger.info("Conexión a Redis establecida")
            
            # Inicialización de MongoDB
            try:
                mongo_uri = st.secrets["connections"]["mongodb"]["uri"]
                logger.info("Usando URI de MongoDB desde Streamlit secrets")
            except:
                load_dotenv()
                mongo_uri = os.getenv('MONGODB_URI')
                if not mongo_uri:
                    raise ValueError("No se encontró la URI de MongoDB")
                logger.info("Usando URI de MongoDB desde variables de entorno")

            # Configuración optimizada de MongoDB
            mongo_options = {
                'connectTimeoutMS': 5000,
                'socketTimeoutMS': 10000,
                'serverSelectionTimeoutMS': 5000,
                'maxPoolSize': 10,
                'minPoolSize': 3,
                'maxIdleTimeMS': 300000,
                'waitQueueTimeoutMS': 5000,
                'appName': 'MigracionesApp',
                'retryWrites': True,
                'retryReads': True,
                'w': 'majority',
                'readPreference': 'primaryPreferred'
            }
            
            # Inicializar cliente MongoDB
            _self.client = MongoClient(mongo_uri, **mongo_options)
            
            # Inicializar bases de datos
            _self.migraciones_db = _self.client['migraciones_db']
            _self.expedientes_db = _self.client['expedientes_db']
            
            # Verificar conexiones
            _self.migraciones_db.command('ping')
            _self.expedientes_db.command('ping')
            
            # Configurar índices
            _self.setup_indexes()
            
            # Inicializar Pool de workers
            _self.thread_pool = ThreadPoolExecutor(max_workers=NUM_WORKERS)
            _self.process_pool = ProcessPoolExecutor(max_workers=NUM_WORKERS)
            
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
        """Fuerza actualización limpiando el cache y recargando datos en paralelo."""
        if not _self.verify_password(password):
            st.error("Contraseña incorrecta")
            return False
        
        try:
            # Limpiar cache de Redis
            _self.redis_client.flushdb()
            logger.info("Cache de Redis limpiado")
            
            # Cargar datos frescos para cada módulo en paralelo
            modules = ['CCM', 'CCM-ESP', 'PRR', 'SOL']
            
            with st.spinner("Actualizando datos..."):
                # Usar ThreadPoolExecutor para operaciones I/O
                with _self.thread_pool as executor:
                    # Cargar módulos en paralelo
                    future_to_module = {
                        executor.submit(_self._load_fresh_data, module): module 
                        for module in modules
                    }
                    
                    # Procesar resultados
                    results = {}
                    for future in future_to_module:
                        module = future_to_module[future]
                        try:
                            data = future.result()
                            if data is not None:
                                results[module] = data
                                _self._cache_data(module, data)
                        except Exception as e:
                            logger.error(f"Error procesando {module}: {str(e)}")
                    
                    # Procesar CCM-LEY después de tener CCM y CCM-ESP
                    if 'CCM' in results and 'CCM-ESP' in results:
                        ccm_ley_data = results['CCM'][
                            ~results['CCM']['NumeroTramite'].isin(
                                results['CCM-ESP']['NumeroTramite']
                            )
                        ]
                        _self._cache_data('CCM-LEY', ccm_ley_data)
            
            st.success("✅ Datos actualizados y cacheados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error en actualización: {str(e)}")
            st.error(f"Error al actualizar datos: {str(e)}")
            return False

    def _process_chunk(_self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Procesa un chunk de datos en paralelo."""
        # Convertir fechas
        for col in DATE_COLUMNS:
            if col in chunk.columns:
                chunk[col] = pd.to_datetime(chunk[col], format='%d/%m/%Y', errors='coerce')
        
        # Optimizar tipos de datos
        return _self._optimize_dtypes(chunk)

    def _load_fresh_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos frescos desde MongoDB usando procesamiento paralelo."""
        try:
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            collection = _self.migraciones_db[collection_name]
            
            # Obtener total de documentos
            total_docs = collection.count_documents({})
            chunk_size = max(5000, total_docs // (NUM_WORKERS * 2))
            
            # Dividir la consulta en chunks
            chunks = []
            cursor = collection.find(
                {},
                {'_id': 0},
                batch_size=chunk_size
            ).allow_disk_use(True)

            # Procesar documentos en chunks
            current_chunk = []
            for doc in cursor:
                current_chunk.append(doc)
                if len(current_chunk) >= chunk_size:
                    chunks.append(pd.DataFrame(current_chunk))
                    current_chunk = []

            if current_chunk:
                chunks.append(pd.DataFrame(current_chunk))

            # Procesar chunks en paralelo
            if chunks:
                # Usar ProcessPoolExecutor para procesamiento CPU-intensivo
                with _self.process_pool as executor:
                    processed_chunks = list(executor.map(_self._process_chunk, chunks))
                
                # Combinar resultados
                data = pd.concat(processed_chunks, ignore_index=True)
                return data
            
            return None

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
        try:
            # Dividir el DataFrame en chunks para procesamiento paralelo
            num_chunks = NUM_WORKERS
            chunk_size = len(df) // num_chunks
            chunks = np.array_split(df, num_chunks)
            
            def optimize_chunk(chunk):
                # Optimizar tipos numéricos
                for col in chunk.select_dtypes(include=['int64']).columns:
                    if chunk[col].min() >= 0:
                        if chunk[col].max() < 255:
                            chunk[col] = chunk[col].astype('uint8')
                        elif chunk[col].max() < 65535:
                            chunk[col] = chunk[col].astype('uint16')
                        else:
                            chunk[col] = chunk[col].astype('uint32')
                    else:
                        if chunk[col].min() > -128 and chunk[col].max() < 127:
                            chunk[col] = chunk[col].astype('int8')
                        elif chunk[col].min() > -32768 and chunk[col].max() < 32767:
                            chunk[col] = chunk[col].astype('int16')
                        else:
                            chunk[col] = chunk[col].astype('int32')

                # Optimizar columnas de texto
                for col in chunk.select_dtypes(include=['object']).columns:
                    if chunk[col].nunique() / len(chunk) < 0.5:
                        chunk[col] = pd.Categorical(chunk[col])
                
                return chunk

            # Procesar chunks en paralelo
            with _self.process_pool as executor:
                optimized_chunks = list(executor.map(optimize_chunk, chunks))
            
            # Combinar resultados
            return pd.concat(optimized_chunks, ignore_index=True)
            
        except Exception as e:
            logger.error(f"Error en optimización de tipos: {str(e)}")
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