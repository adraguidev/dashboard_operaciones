import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS, MODULES, CACHE_TTL
from dotenv import load_dotenv
import logging
import time
import hashlib

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
                'compressors': ['zlib'],
                'retryWrites': True,
                'retryReads': True,
                'w': 'majority',
                'readPreference': 'primaryPreferred'
            }
            
            _self.client = MongoClient(mongo_uri, **mongo_options)
            
            # Base de datos para datos consolidados
            _self.migraciones_db = _self.client['migraciones_db']
            # Base de datos para rankings
            _self.expedientes_db = _self.client['expedientes_db']
            
            # Verificar conexiones con timeout
            _self.migraciones_db.command('ping', maxTimeMS=5000)
            _self.expedientes_db.command('ping', maxTimeMS=5000)
            
            # Configurar índices para optimizar consultas
            _self.setup_indexes()
            
            # Configurar colección de caché
            _self.setup_cache_collection()
            
            logger.info("Conexión exitosa a MongoDB")
        except Exception as e:
            logger.error(f"Error detallado de conexión: {str(e)}")
            st.error(f"Error al conectar con MongoDB: {str(e)}")
            raise

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

    def setup_cache_collection(_self):
        """Configura la colección de caché y sus índices."""
        try:
            cache_collection = _self.migraciones_db[MONGODB_COLLECTIONS['CACHE']]
            
            # Crear índices para la colección de caché
            cache_collection.create_index([
                ("module", 1),
                ("timestamp", 1)
            ], background=True)
            
            # Crear índice TTL para limpiar datos antiguos
            cache_collection.create_index(
                "timestamp",
                expireAfterSeconds=CACHE_TTL * 60,
                background=True
            )
            
            logger.info("Colección de caché configurada correctamente")
        except Exception as e:
            logger.error(f"Error al configurar colección de caché: {str(e)}")

    def _get_cached_data(_self, module_name: str) -> pd.DataFrame:
        """Intenta obtener datos cacheados de MongoDB."""
        try:
            cache_collection = _self.migraciones_db[MONGODB_COLLECTIONS['CACHE']]
            
            # Buscar datos cacheados
            cached_data = cache_collection.find_one({
                "module": module_name,
                "timestamp": {"$gt": datetime.now() - pd.Timedelta(minutes=CACHE_TTL)}
            })
            
            if cached_data:
                logger.info(f"Datos encontrados en caché para {module_name}")
                # Convertir los datos BSON a DataFrame
                df = pd.DataFrame(cached_data['data'])
                
                # Convertir fechas
                for col in DATE_COLUMNS:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col])
                
                return df
            
            return None
        except Exception as e:
            logger.error(f"Error al obtener datos cacheados: {str(e)}")
            return None

    def _save_to_cache(_self, module_name: str, data: pd.DataFrame):
        """Guarda los datos procesados en el caché de MongoDB."""
        try:
            if data is None or data.empty:
                logger.warning(f"No hay datos para cachear del módulo {module_name}")
                return
            
            cache_collection = _self.migraciones_db[MONGODB_COLLECTIONS['CACHE']]
            
            # Convertir DataFrame a formato serializable
            data_dict = data.to_dict('records')
            
            # Guardar en caché
            cache_collection.update_one(
                {"module": module_name},
                {
                    "$set": {
                        "module": module_name,
                        "timestamp": datetime.now(),
                        "data": data_dict
                    }
                },
                upsert=True
            )
            
            logger.info(f"Datos guardados en caché para {module_name}")
        except Exception as e:
            logger.error(f"Error al guardar en caché: {str(e)}")

    def verify_password(_self, password: str) -> bool:
        """Verifica si la contraseña proporcionada es correcta."""
        correct_password = "Ka260314!"
        return password == correct_password

    def force_data_refresh(_self, password: str) -> bool:
        """Fuerza una actualización de datos si la contraseña es correcta."""
        return _self.refresh_cache_in_background(password)

    @st.cache_data(ttl=60)  # Cache de Streamlit por 1 hora como respaldo
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos consolidados desde migraciones_db con caché en MongoDB."""
        try:
            # SPE tiene su propia lógica de carga
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            logger.info(f"Cargando datos para módulo: {module_name}")
            
            # Intentar obtener datos del caché
            cached_data = _self._get_cached_data(module_name)
            if cached_data is not None:
                logger.info(f"Usando datos cacheados para {module_name}")
                return cached_data
            
            # Si no hay caché, procesar normalmente
            if module_name == 'CCM-LEY':
                # Procesar CCM-LEY
                ccm_data = _self.load_module_data('CCM')
                ccm_esp_data = _self.load_module_data('CCM-ESP')
                
                if ccm_data is None or ccm_esp_data is None:
                    return None
                
                data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])].copy()
                
                # Guardar en caché
                _self._save_to_cache(module_name, data)
                return data
            
            # Procesar otros módulos
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            collection = _self.migraciones_db[collection_name]
            cursor = collection.find(
                {},
                {'_id': 0},
                batch_size=5000,
                hint=[("FechaExpendiente", 1)]
            ).allow_disk_use(True)

            chunks = []
            chunk_size = 10000
            current_chunk = []
            
            for doc in cursor:
                current_chunk.append(doc)
                if len(current_chunk) >= chunk_size:
                    df_chunk = pd.DataFrame(current_chunk)
                    df_chunk = _self._optimize_dtypes(df_chunk)
                    chunks.append(df_chunk)
                    current_chunk = []

            if current_chunk:
                df_chunk = pd.DataFrame(current_chunk)
                df_chunk = _self._optimize_dtypes(df_chunk)
                chunks.append(df_chunk)

            if not chunks:
                return None

            data = pd.concat(chunks, ignore_index=True)
            
            # Procesar fechas
            for col in DATE_COLUMNS:
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce')
            
            # Guardar en caché
            _self._save_to_cache(module_name, data)
            
            return data

        except Exception as e:
            logger.error(f"Error al cargar datos del módulo {module_name}: {str(e)}")
            st.error(f"Error al cargar datos del módulo {module_name}: {str(e)}")
            return None

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

    def refresh_cache_in_background(_self, password: str) -> bool:
        """Actualiza el caché en el backend para todos los módulos."""
        if not _self.verify_password(password):
            st.error("Contraseña incorrecta")
            return False
        
        try:
            # Mostrar barra de progreso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Lista de módulos a actualizar (excluyendo SPE que tiene su propia lógica)
            modules_to_update = [mod for mod in MODULES.keys() if mod != 'SPE']
            total_modules = len(modules_to_update)
            
            logger.info(f"Iniciando actualización de caché para {total_modules} módulos")
            
            for idx, module in enumerate(modules_to_update):
                try:
                    status_text.text(f"Actualizando caché de {MODULES[module]}...")
                    logger.info(f"Procesando módulo: {module}")
                    
                    # Limpiar caché existente para este módulo
                    cache_collection = _self.migraciones_db[MONGODB_COLLECTIONS['CACHE']]
                    cache_collection.delete_one({"module": module})
                    logger.info(f"Caché limpiado para {module}")
                    
                    # Cargar datos frescos
                    if module == 'CCM-LEY':
                        # Procesar CCM-LEY
                        logger.info("Cargando datos para CCM-LEY...")
                        ccm_data = _self._load_fresh_data('CCM')
                        ccm_esp_data = _self._load_fresh_data('CCM-ESP')
                        
                        if ccm_data is not None and ccm_esp_data is not None:
                            data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])].copy()
                            _self._save_to_cache(module, data)
                            logger.info(f"Datos de CCM-LEY procesados: {len(data)} registros")
                    else:
                        # Cargar datos frescos para otros módulos
                        data = _self._load_fresh_data(module)
                        if data is not None:
                            _self._save_to_cache(module, data)
                            logger.info(f"Datos de {module} procesados: {len(data)} registros")
                    
                    # Actualizar progreso
                    progress = (idx + 1) / total_modules
                    progress_bar.progress(progress)
                    
                except Exception as e:
                    logger.error(f"Error actualizando caché para {module}: {str(e)}")
                    st.error(f"Error en módulo {MODULES[module]}: {str(e)}")
                    continue
            
            # Limpiar caché de Streamlit
            st.cache_data.clear()
            logger.info("Caché de Streamlit limpiado")
            
            status_text.text("✅ Caché actualizado completamente")
            time.sleep(1)  # Pequeña pausa para mostrar el mensaje final
            status_text.empty()
            progress_bar.empty()
            
            return True
            
        except Exception as e:
            logger.error(f"Error en la actualización del caché: {str(e)}")
            st.error(f"Error en la actualización del caché: {str(e)}")
            return False

    def _load_fresh_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos frescos desde MongoDB sin usar caché."""
        try:
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            collection = _self.migraciones_db[collection_name]
            cursor = collection.find(
                {},
                {'_id': 0},
                batch_size=5000,
                hint=[("FechaExpendiente", 1)]
            ).allow_disk_use(True)

            chunks = []
            chunk_size = 10000
            current_chunk = []
            
            for doc in cursor:
                current_chunk.append(doc)
                if len(current_chunk) >= chunk_size:
                    df_chunk = pd.DataFrame(current_chunk)
                    df_chunk = _self._optimize_dtypes(df_chunk)
                    chunks.append(df_chunk)
                    current_chunk = []

            if current_chunk:
                df_chunk = pd.DataFrame(current_chunk)
                df_chunk = _self._optimize_dtypes(df_chunk)
                chunks.append(df_chunk)

            if not chunks:
                return None

            data = pd.concat(chunks, ignore_index=True)
            
            # Procesar fechas
            for col in DATE_COLUMNS:
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce')
            
            return data

        except Exception as e:
            logger.error(f"Error al cargar datos frescos del módulo {module_name}: {str(e)}")
            return None