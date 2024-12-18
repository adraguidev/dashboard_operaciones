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
        try:
            # Convertir fechas eficientemente usando vectorización
            for col in DATE_COLUMNS:
                if col in chunk.columns:
                    # Primero intentar formato estándar
                    try:
                        chunk[col] = pd.to_datetime(chunk[col], format='%d/%m/%Y')
                    except:
                        # Si falla, usar el parser más flexible
                        chunk[col] = pd.to_datetime(chunk[col], errors='coerce')
            
            # Optimizar tipos de datos
            chunk = _self._optimize_dtypes(chunk)
            
            # Asegurar tipos de datos específicos para columnas críticas
            if 'NumeroTramite' in chunk.columns:
                chunk['NumeroTramite'] = chunk['NumeroTramite'].astype(str)
            if 'EVALASIGN' in chunk.columns:
                chunk['EVALASIGN'] = chunk['EVALASIGN'].fillna('').astype(str)
            if 'Evaluado' in chunk.columns:
                chunk['Evaluado'] = chunk['Evaluado'].fillna('NO').astype(str)
            if 'ESTADO' in chunk.columns:
                chunk['ESTADO'] = chunk['ESTADO'].fillna('').astype(str)
            
            return chunk
        except Exception as e:
            logger.error(f"Error procesando chunk: {str(e)}")
            return None

    def _load_fresh_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos frescos desde MongoDB usando pipeline de agregación."""
        try:
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            collection = _self.migraciones_db[collection_name]
            
            # Pipeline de agregación para pre-procesar datos en MongoDB
            pipeline = [
                # Proyectar solo los campos necesarios y convertir tipos
                {
                    "$project": {
                        "NumeroTramite": {"$toString": "$NumeroTramite"},
                        "FechaExpendiente": 1,
                        "FechaPre": 1,
                        "FechaTramite": 1,
                        "FechaAsignacion": 1,
                        "EVALASIGN": {"$ifNull": ["$EVALASIGN", ""]},
                        "Evaluado": {"$ifNull": ["$Evaluado", "NO"]},
                        "ESTADO": {"$ifNull": ["$ESTADO", ""]},
                        "UltimaEtapa": 1,
                        "Anio": {"$ifNull": ["$Anio", 0]},
                        "Mes": {"$ifNull": ["$Mes", 0]}
                    }
                },
                # Usar allowDiskUse para grandes conjuntos de datos
                {"$allowDiskUse": True}
            ]
            
            # Ejecutar agregación en chunks
            chunk_size = 50000
            data_chunks = []
            
            with _self.thread_pool as executor:
                futures = []
                
                def process_cursor(cursor):
                    chunk_data = list(cursor)
                    if chunk_data:
                        df = pd.DataFrame(chunk_data)
                        # Convertir fechas de manera más eficiente
                        for col in DATE_COLUMNS:
                            if col in df.columns:
                                df[col] = pd.to_datetime(df[col], format='%Y-%m-%d', errors='coerce')
                        return df
                    return None

                # Dividir la consulta en chunks usando skip/limit
                total_docs = collection.count_documents({})
                for skip in range(0, total_docs, chunk_size):
                    chunk_pipeline = pipeline + [
                        {"$skip": skip},
                        {"$limit": chunk_size}
                    ]
                    cursor = collection.aggregate(chunk_pipeline)
                    futures.append(executor.submit(process_cursor, cursor))

                # Procesar resultados
                for future in futures:
                    try:
                        chunk_df = future.result(timeout=300)
                        if chunk_df is not None and not chunk_df.empty:
                            data_chunks.append(chunk_df)
                    except Exception as e:
                        logger.error(f"Error procesando chunk: {str(e)}")

            # Combinar chunks si hay datos
            if data_chunks:
                final_df = pd.concat(data_chunks, ignore_index=True)
                
                # Optimizar tipos de datos una sola vez al final
                final_df = _self._optimize_dtypes(final_df)
                
                return final_df
            
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
        """Optimiza los tipos de datos del DataFrame de manera más eficiente."""
        try:
            # Optimizar tipos numéricos de manera vectorizada
            int_cols = df.select_dtypes(include=['int64']).columns
            if not int_cols.empty:
                # Calcular min/max una sola vez por columna
                mins = df[int_cols].min()
                maxs = df[int_cols].max()
                
                for col in int_cols:
                    min_val = mins[col]
                    max_val = maxs[col]
                    
                    if min_val >= 0:
                        if max_val < 255:
                            df[col] = df[col].astype('uint8')
                        elif max_val < 65535:
                            df[col] = df[col].astype('uint16')
                        else:
                            df[col] = df[col].astype('uint32')
                    else:
                        if min_val > -128 and max_val < 127:
                            df[col] = df[col].astype('int8')
                        elif min_val > -32768 and max_val < 32767:
                            df[col] = df[col].astype('int16')
                        else:
                            df[col] = df[col].astype('int32')

            # Optimizar columnas de texto de manera vectorizada
            obj_cols = df.select_dtypes(include=['object']).columns
            if not obj_cols.empty:
                # Calcular proporción de valores únicos una sola vez
                nunique = df[obj_cols].nunique()
                total_rows = len(df)
                
                for col in obj_cols:
                    if nunique[col] / total_rows < 0.5:
                        df[col] = pd.Categorical(df[col])

            return df
            
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