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
            
            # Iniciar precarga asíncrona de datos
            _self._start_async_preload()
            
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
        """Almacena datos en Redis con compresión optimizada y persistente."""
        try:
            cache_key = _self._get_cache_key(module_name)
            
            # Verificar espacio disponible
            current_size = _self._get_cache_size()
            if current_size > (REDIS_MEMORY_LIMIT * 0.9):
                logger.warning("Cache casi lleno, limpiando datos antiguos...")
                _self._clear_old_cache()
            
            # Optimizar DataFrame antes de serializar
            data = _self._optimize_dtypes(data)
            
            # Serializar DataFrame con compresión máxima
            import zlib
            serialized_data = zlib.compress(pickle.dumps(data), level=9)
            
            # Guardar en Redis sin TTL (persistente hasta actualización manual)
            success = _self.redis_client.set(cache_key, serialized_data)
            
            if success:
                # Guardar metadata
                metadata = {
                    'rows': len(data),
                    'columns': list(data.columns),
                    'cached_at': datetime.now().isoformat(),
                    'size_mb': len(serialized_data) / 1024 / 1024,
                    'version': '1.0'  # Para control de versiones del cache
                }
                metadata_key = _self._get_cache_key(module_name, 'metadata')
                _self.redis_client.set(metadata_key, json.dumps(metadata))
                
                logger.info(f"Datos cacheados para {module_name}: {len(data)} registros, {metadata['size_mb']:.2f}MB")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al cachear datos: {str(e)}")
            return False

    def _get_cached_data(_self, module_name: str) -> pd.DataFrame:
        """Recupera datos cacheados de Redis con descompresión."""
        try:
            cache_key = _self._get_cache_key(module_name)
            cached_data = _self.redis_client.get(cache_key)
            
            if cached_data:
                # Descomprimir y deserializar
                import zlib
                data = pickle.loads(zlib.decompress(cached_data))
                
                # Obtener metadata
                metadata_key = _self._get_cache_key(module_name, 'metadata')
                metadata = _self.redis_client.get(metadata_key)
                if metadata:
                    metadata = json.loads(metadata)
                    logger.info(f"Usando cache para {module_name} - {metadata['rows']} registros, {metadata['size_mb']:.2f}MB")
                
                return data
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
            
            # Cargar datos frescos en paralelo
            import concurrent.futures
            modules = ['CCM', 'CCM-ESP', 'PRR', 'SOL']
            
            with st.spinner("Actualizando datos..."):
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    # Cargar módulos en paralelo
                    future_to_module = {
                        executor.submit(_self._load_and_cache_module, module): module 
                        for module in modules
                    }
                    
                    # Esperar resultados
                    for future in concurrent.futures.as_completed(future_to_module):
                        module = future_to_module[future]
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Error actualizando {module}: {str(e)}")
                    
                    # Procesar CCM-LEY después de que CCM y CCM-ESP estén listos
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
        """Carga datos con soporte de cache Redis optimizado."""
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

    def _start_async_preload(_self):
        """Inicia la precarga asíncrona de datos en Redis."""
        import threading
        thread = threading.Thread(target=_self._preload_data)
        thread.daemon = True
        thread.start()

    def _preload_data(_self):
        """Precarga datos en Redis de manera optimizada."""
        try:
            # Orden de prioridad de módulos (basado en uso común)
            priority_modules = ['CCM', 'CCM-ESP', 'PRR', 'SOL']
            
            for module in priority_modules:
                if not _self._is_module_cached(module):
                    data = _self._load_fresh_data(module)
                    if data is not None:
                        # Optimizar tipos de datos antes de cachear
                        data = _self._optimize_dtypes(data)
                        _self._cache_data(module, data)
                        
            # Procesar CCM-LEY después de CCM y CCM-ESP
            if not _self._is_module_cached('CCM-LEY'):
                ccm_data = _self._get_cached_data('CCM')
                ccm_esp_data = _self._get_cached_data('CCM-ESP')
                if ccm_data is not None and ccm_esp_data is not None:
                    ccm_ley_data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
                    ccm_ley_data = _self._optimize_dtypes(ccm_ley_data)
                    _self._cache_data('CCM-LEY', ccm_ley_data)
            
            logger.info("Precarga de datos completada")
        except Exception as e:
            logger.error(f"Error en precarga: {str(e)}")

    def _is_module_cached(_self, module_name: str) -> bool:
        """Verifica si un módulo está en cache y es válido."""
        try:
            cache_key = _self._get_cache_key(module_name)
            return _self.redis_client.exists(cache_key) == 1
        except:
            return False

    def _clear_old_cache(_self):
        """Limpia el cache de manera inteligente."""
        try:
            # Obtener todas las claves y sus metadatos
            all_keys = _self.redis_client.keys("migraciones:*:data") + _self.redis_client.keys("migraciones:*:processed_*")
            modules_info = []
            
            for key in all_keys:
                key_parts = key.decode().split(':')
                module = key_parts[1]
                operation = key_parts[2] if len(key_parts) > 2 else 'data'
                
                metadata_key = _self._get_cache_key(module, f"{operation}_meta")
                metadata = _self.redis_client.get(metadata_key)
                
                if metadata:
                    metadata = json.loads(metadata)
                    modules_info.append({
                        'module': module,
                        'operation': operation,
                        'size': metadata.get('size_mb', 0),
                        'last_access': metadata.get('cached_at'),
                        'is_processed': 'processed' in operation
                    })
            
            # Ordenar dando prioridad a datos sin procesar y más recientes
            modules_info.sort(key=lambda x: (
                x['is_processed'],  # Primero eliminar datos procesados
                x['last_access'],   # Luego los más antiguos
                -x['size']          # Finalmente los más grandes
            ))
            
            # Eliminar módulos hasta liberar suficiente espacio
            for module_info in modules_info:
                module = module_info['module']
                operation = module_info['operation']
                _self.redis_client.delete(
                    _self._get_cache_key(module, operation),
                    _self._get_cache_key(module, f"{operation}_meta")
                )
                logger.info(f"Cache limpiado para {module}:{operation}")
                
                current_size = _self._get_cache_size()
                if current_size < (REDIS_MEMORY_LIMIT * 0.7):
                    break
                    
        except Exception as e:
            logger.error(f"Error al limpiar cache: {str(e)}")
            _self.redis_client.flushdb()  # Si algo falla, limpiar todo

    def cache_processed_data(_self, module_name: str, data: pd.DataFrame, process_type: str) -> bool:
        """Almacena datos procesados en Redis de manera persistente."""
        try:
            cache_key = _self._get_cache_key(module_name, f"processed_{process_type}")
            
            # Optimizar y serializar DataFrame
            data = _self._optimize_dtypes(data)
            import zlib
            serialized_data = zlib.compress(pickle.dumps(data), level=9)
            
            # Guardar en Redis sin TTL (persistente)
            success = _self.redis_client.set(cache_key, serialized_data)
            
            if success:
                metadata = {
                    'rows': len(data),
                    'process_type': process_type,
                    'cached_at': datetime.now().isoformat(),
                    'size_mb': len(serialized_data) / 1024 / 1024,
                    'version': '1.0'
                }
                metadata_key = _self._get_cache_key(module_name, f"processed_{process_type}_meta")
                _self.redis_client.set(metadata_key, json.dumps(metadata))
                
                logger.info(f"Datos procesados cacheados para {module_name}:{process_type}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error al cachear datos procesados: {str(e)}")
            return False

    def get_processed_data(_self, module_name: str, process_type: str) -> pd.DataFrame:
        """Recupera datos procesados del cache."""
        try:
            cache_key = _self._get_cache_key(module_name, f"processed_{process_type}")
            cached_data = _self.redis_client.get(cache_key)
            
            if cached_data:
                # Descomprimir y deserializar
                import zlib
                data = pickle.loads(zlib.decompress(cached_data))
                
                # Verificar metadata
                metadata_key = _self._get_cache_key(module_name, f"processed_{process_type}_meta")
                metadata = _self.redis_client.get(metadata_key)
                if metadata:
                    metadata = json.loads(metadata)
                    logger.info(f"Usando cache procesado para {module_name}:{process_type}")
                
                return data
            return None
        except Exception as e:
            logger.error(f"Error al recuperar datos procesados: {str(e)}")
            return None

    def prepare_common_data(_self, module_name: str, data: pd.DataFrame) -> pd.DataFrame:
        """Prepara los datos comunes con soporte de cache persistente."""
        try:
            # Intentar obtener datos preprocesados del cache
            processed_data = _self.get_processed_data(module_name, "common")
            if processed_data is not None:
                return processed_data

            # Si no hay cache, procesar los datos
            logger.info(f"Procesando datos comunes para {module_name}...")
            
            # Procesar datos de manera más eficiente
            data = data.copy()
            
            # Convertir fechas usando un método más rápido
            for col in DATE_COLUMNS:
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce', cache=True)
            
            # Optimizar tipos de datos
            data = _self._optimize_dtypes(data)
            
            # Cachear los resultados
            _self.cache_processed_data(module_name, data, "common")
            
            return data
            
        except Exception as e:
            logger.error(f"Error en prepare_common_data: {str(e)}")
            return data

    def _load_and_cache_module(_self, module_name: str) -> None:
        """Helper para cargar y cachear un módulo en paralelo."""
        data = _self._load_fresh_data(module_name)
        if data is not None:
            _self._cache_data(module_name, data)
            # Pre-procesar datos comunes
            _self.prepare_common_data(module_name, data)