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
                'maxPoolSize': 10,  # Aumentado para mejor concurrencia
                'minPoolSize': 3,   # Aumentado ligeramente
                'maxIdleTimeMS': 300000,
                'waitQueueTimeoutMS': 5000,
                'appName': 'MigracionesApp',
                'compressors': ['zlib'],
                'retryWrites': True,
                'retryReads': True,
                'w': 'majority',    # Garantizar consistencia
                'readPreference': 'primaryPreferred'  # Mejor rendimiento en lecturas
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

    def verify_password(_self, password: str) -> bool:
        """Verifica si la contraseña proporcionada es correcta."""
        correct_password = "Ka260314!"
        return password == correct_password

    def force_data_refresh(_self, password: str) -> bool:
        """Fuerza una actualización de datos si la contraseña es correcta."""
        if not _self.verify_password(password):
            st.error("Contraseña incorrecta")
            return False
        
        try:
            # Limpiar solo el caché de Streamlit
            st.cache_data.clear()
            st.success("✅ Datos actualizados correctamente")
            return True
        except Exception as e:
            st.error(f"Error al actualizar datos: {str(e)}")
            return False

    @st.cache_data(ttl=None, persist="disk")  # Cache permanente y persistente en disco
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos consolidados desde migraciones_db."""
        try:
            # SPE tiene su propia lógica de carga separada
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            logger.info(f"Cargando datos para módulo: {module_name}")
            start_time = time.time()

            # Procesamiento especial para CCM-LEY
            if module_name == 'CCM-LEY':
                logger.info("Iniciando carga de CCM-LEY...")
                ccm_data = _self.load_module_data('CCM')
                ccm_esp_data = _self.load_module_data('CCM-ESP')
                
                if ccm_data is None or ccm_esp_data is None:
                    return None
                    
                data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])].copy()
                return data

            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            collection = _self.migraciones_db[collection_name]
            
            # Optimizar la consulta usando cursor con batch_size
            cursor = collection.find(
                {},
                {'_id': 0},
                batch_size=10000  # Aumentamos el batch_size para reducir viajes a la BD
            ).hint([("FechaExpendiente", 1)])  # Usar índice para mejor rendimiento
            
            # Usar pandas para leer el cursor directamente
            data = pd.DataFrame(list(cursor))
            if data.empty:
                st.error(f"No se encontraron datos para el módulo {module_name}")
                return None

            # Optimizar tipos de datos inmediatamente después de cargar
            data = _self._optimize_dtypes(data)
            
            # Convertir fechas de manera más eficiente
            for col in DATE_COLUMNS:
                if col in data.columns:
                    data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce')

            elapsed_time = time.time() - start_time
            logger.info(f"Carga de {module_name} completada en {elapsed_time:.2f} segundos")
            logger.info(f"Registros cargados: {len(data)}")
            
            return data

        except Exception as e:
            logger.error(f"Error al cargar datos del módulo {module_name}: {str(e)}")
            st.error(f"Error al cargar datos del módulo {module_name}: {str(e)}")
            return None

    def _optimize_dtypes(_self, df: pd.DataFrame) -> pd.DataFrame:
        """Optimiza los tipos de datos del DataFrame para reducir uso de memoria."""
        try:
            # Optimizar tipos numéricos
            for col in df.select_dtypes(include=['int64', 'float64']).columns:
                # Intentar convertir a entero si no hay decimales
                if df[col].dtype == 'float64' and df[col].notnull().all() and (df[col] % 1 == 0).all():
                    df[col] = df[col].astype('int32')
                # Optimizar enteros
                elif df[col].dtype == 'int64':
                    df[col] = pd.to_numeric(df[col], downcast='integer')

            # Optimizar strings usando categorías para valores repetidos
            for col in df.select_dtypes(include=['object']).columns:
                num_unique = df[col].nunique()
                if num_unique < len(df) * 0.5:  # Si hay menos de 50% de valores únicos
                    df[col] = df[col].astype('category')

            return df
        except Exception as e:
            logger.warning(f"Error en optimización de tipos: {str(e)}")
            return df  # Retornar el DataFrame original si hay error

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