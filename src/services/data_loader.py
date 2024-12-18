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
    _instance = None
    _is_initialized = False
    _client = None
    _migraciones_db = None
    _expedientes_db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataLoader, cls).__new__(cls)
        return cls._instance

    def __init__(_self):
        """Inicializa las conexiones a MongoDB usando los secrets de Streamlit o variables de entorno."""
        if DataLoader._is_initialized:
            return
            
        try:
            # Primero intentar obtener la URI desde secrets de Streamlit
            try:
                mongo_uri = st.secrets["connections"]["mongodb"]["uri"]
            except:
                load_dotenv()
                mongo_uri = os.getenv('MONGODB_URI')
                if not mongo_uri:
                    raise ValueError("No se encontró la URI de MongoDB")

            # Configuración mínima para conexión inicial
            mongo_options = {
                'connectTimeoutMS': 1000,
                'socketTimeoutMS': 2000,
                'serverSelectionTimeoutMS': 1000,
                'maxPoolSize': 3,
                'minPoolSize': 1,
                'maxIdleTimeMS': 300000,
                'waitQueueTimeoutMS': 1000,
                'appName': 'MigracionesApp',
                'retryWrites': True,
                'retryReads': True,
                'w': 'majority',
                'readPreference': 'primaryPreferred'
            }
            
            if not DataLoader._client:
                DataLoader._client = MongoClient(mongo_uri, **mongo_options)
                DataLoader._migraciones_db = DataLoader._client['migraciones_db']
                DataLoader._expedientes_db = DataLoader._client['expedientes_db']
            
            _self.client = DataLoader._client
            _self.migraciones_db = DataLoader._migraciones_db
            _self.expedientes_db = DataLoader._expedientes_db
            
            DataLoader._is_initialized = True
            
        except Exception as e:
            logger.error(f"Error de conexión: {str(e)}")
            st.error("Error al conectar con la base de datos")
            raise

    def ensure_background_init(_self):
        """Asegura que la inicialización en segundo plano se complete."""
        if st.session_state.get('init_background', False):
            try:
                # Configurar índices para optimizar consultas
                _self.setup_indexes()
                # Configurar colección de caché
                _self.setup_cache_collection()
                st.session_state['init_background'] = False
                logger.info("Inicialización en segundo plano completada")
            except Exception as e:
                logger.error(f"Error en inicialización en segundo plano: {str(e)}")

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
        """Intenta obtener datos cacheados."""
        try:
            # Verificar primero en session_state
            cache_key = f"cached_data_{module_name}"
            if cache_key in st.session_state:
                return st.session_state[cache_key]

            # Si no está en session_state, buscar en MongoDB
            cache_collection = _self.migraciones_db[MONGODB_COLLECTIONS['CACHE']]
            cached_data = cache_collection.find_one(
                {"module": module_name},
                {"_id": 0, "data": 1}  # Solo traer los datos necesarios
            )
            
            if cached_data and 'data' in cached_data:
                df = pd.DataFrame(cached_data['data'])
                if not df.empty:
                    # Convertir fechas de manera más eficiente
                    date_cols = [col for col in DATE_COLUMNS if col in df.columns]
                    if date_cols:
                        df[date_cols] = df[date_cols].apply(pd.to_datetime, errors='coerce')
                    
                    # Guardar en session_state
                    st.session_state[cache_key] = df
                    return df
            
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener caché: {str(e)}")
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

    @st.cache_data(ttl=None, show_spinner=False)
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
                return cached_data
            
            logger.info(f"No se encontró caché para {module_name}, cargando datos frescos...")
            
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
            data = _self._load_fresh_data(module_name)
            if data is not None:
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
            # Lista de módulos a actualizar (excluyendo SPE que tiene su propia lógica)
            modules_to_update = [mod for mod in MODULES.keys() if mod != 'SPE']
            total_modules = len(modules_to_update)
            
            logger.info(f"Iniciando actualización de caché para {total_modules} módulos")
            
            # Crear contenedores para la UI
            progress_container = st.empty()
            status_container = st.empty()
            detail_container = st.empty()
            
            with st.spinner("Actualizando caché del sistema..."):
                for idx, module in enumerate(modules_to_update):
                    try:
                        # Actualizar mensajes de estado
                        status_container.info(f"⏳ Actualizando {MODULES[module]}...")
                        detail_container.text(f"Procesando datos...")
                        
                        # Actualizar barra de progreso
                        progress = (idx) / total_modules
                        progress_container.progress(progress)
                        
                        logger.info(f"Procesando módulo: {module}")
                        
                        # Limpiar caché existente para este módulo
                        cache_collection = _self.migraciones_db[MONGODB_COLLECTIONS['CACHE']]
                        cache_collection.delete_one({"module": module})
                        logger.info(f"Caché limpiado para {module}")
                        detail_container.text(f"Caché anterior limpiado...")
                        
                        # Cargar datos frescos
                        if module == 'CCM-LEY':
                            # Procesar CCM-LEY
                            logger.info("Cargando datos para CCM-LEY...")
                            detail_container.text(f"Cargando datos de CCM...")
                            ccm_data = _self._load_fresh_data('CCM')
                            detail_container.text(f"Cargando datos de CCM-ESP...")
                            ccm_esp_data = _self._load_fresh_data('CCM-ESP')
                            
                            if ccm_data is not None and ccm_esp_data is not None:
                                detail_container.text(f"Procesando datos...")
                                data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])].copy()
                                _self._save_to_cache(module, data)
                                detail_container.text(f"Guardando en caché...")
                                logger.info(f"Datos de CCM-LEY procesados: {len(data)} registros")
                        else:
                            # Cargar datos frescos para otros módulos
                            detail_container.text(f"Cargando datos frescos...")
                            data = _self._load_fresh_data(module)
                            if data is not None:
                                detail_container.text(f"Guardando en caché...")
                                _self._save_to_cache(module, data)
                                logger.info(f"Datos de {module} procesados: {len(data)} registros")
                        
                        # Actualizar progreso final del módulo
                        progress = (idx + 1) / total_modules
                        progress_container.progress(progress)
                        
                        # Mostrar éxito del módulo
                        status_container.success(f"✅ {MODULES[module]} actualizado")
                        time.sleep(0.5)  # Pequeña pausa para mostrar el éxito
                        
                    except Exception as e:
                        logger.error(f"Error actualizando caché para {module}: {str(e)}")
                        status_container.error(f"❌ Error en {MODULES[module]}: {str(e)}")
                        time.sleep(1)  # Pausa para mostrar el error
                        continue
                
                # Limpiar caché de Streamlit
                st.cache_data.clear()
                logger.info("Caché de Streamlit limpiado")
                
                # Limpiar contenedores
                progress_container.empty()
                detail_container.empty()
                
                # Mostrar mensaje final
                status_container.success("✅ Caché actualizado completamente")
                
                return True
                
        except Exception as e:
            logger.error(f"Error en la actualización del caché: {str(e)}")
            st.error(f"Error en la actualización del caché: {str(e)}")
            return False

    def _load_fresh_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos frescos desde MongoDB."""
        try:
            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                return None

            collection = _self.migraciones_db[collection_name]
            
            # Proyección optimizada
            projection = {'_id': 0}
            
            # Usar cursor con batch_size grande
            cursor = collection.find(
                {},
                projection,
                batch_size=20000,
                hint=[("FechaExpendiente", 1)]
            ).allow_disk_use(True)

            # Procesar en chunks más grandes
            chunks = []
            chunk_size = 50000
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

            # Concatenar chunks eficientemente
            data = pd.concat(chunks, ignore_index=True, copy=False)
            
            # Procesar fechas en un solo paso
            date_cols = [col for col in DATE_COLUMNS if col in data.columns]
            if date_cols:
                data[date_cols] = data[date_cols].apply(pd.to_datetime, errors='coerce')
            
            return data

        except Exception as e:
            logger.error(f"Error cargando datos frescos: {str(e)}")
            return None