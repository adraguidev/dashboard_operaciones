import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener las variables de entorno
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD')

class DataLoader:
    def __init__(_self):
        """Inicializa las conexiones a MongoDB usando los secrets de Streamlit."""
        try:
            # Configurar opciones de MongoDB para mejor manejo de memoria
            _self.client = MongoClient(
                MONGODB_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                maxPoolSize=1,  # Limitar conexiones simultáneas
                maxIdleTimeMS=5000,  # Cerrar conexiones inactivas
                compressors=['zlib']  # Comprimir datos
            )
            _self.migraciones_db = _self.client['migraciones_db']
            _self.expedientes_db = _self.client['expedientes_db']
            _self.migraciones_db.command('ping', maxTimeMS=5000)
            _self.expedientes_db.command('ping', maxTimeMS=5000)
        except Exception as e:
            st.error(f"Error al conectar con MongoDB: {str(e)}")
            raise

    @st.cache_data(ttl=3600, max_entries=100, show_spinner=False)
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos consolidados desde migraciones_db."""
        try:
            # Liberar memoria
            import gc
            gc.collect()

            # Establecer límites de memoria para pandas
            import pandas as pd
            pd.options.mode.chunksize = 1000
            
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()

            # Procesamiento especial para CCM-LEY con manejo de memoria
            if module_name == 'CCM-LEY':
                try:
                    ccm_data = _self.load_module_data('CCM')
                    if ccm_data is None:
                        return None
                    
                    ccm_esp_data = _self.load_module_data('CCM-ESP')
                    if ccm_esp_data is None:
                        return None

                    # Filtrar usando merge para mejor eficiencia de memoria
                    data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
                    del ccm_esp_data  # Liberar memoria
                    gc.collect()
                    
                    if 'TipoTramite' in data.columns:
                        data = data[data['TipoTramite'] == 'LEY'].copy()
                    return data
                except Exception as e:
                    st.error(f"Error en CCM-LEY: {str(e)}")
                    return None

            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            # Cargar datos en chunks con manejo de memoria
            collection = _self.migraciones_db[collection_name]
            chunks = []
            chunk_size = 1000
            total_docs = collection.count_documents({})
            
            for i in range(0, total_docs, chunk_size):
                try:
                    chunk = list(collection.find(
                        {}, 
                        {'_id': 0},
                        skip=i,
                        limit=chunk_size,
                        maxTimeMS=10000
                    ))
                    if not chunk:
                        break
                    
                    df_chunk = pd.DataFrame(chunk)
                    # Optimizar tipos de datos inmediatamente
                    for col in df_chunk.select_dtypes(include=['object']).columns:
                        if df_chunk[col].nunique() / len(df_chunk) < 0.5:
                            df_chunk[col] = df_chunk[col].astype('category')
                    
                    chunks.append(df_chunk)
                    del chunk  # Liberar memoria
                    gc.collect()
                    
                except Exception as e:
                    st.error(f"Error al cargar chunk {i}: {str(e)}")
                    continue

            if not chunks:
                return None

            # Concatenar chunks eficientemente
            try:
                data = pd.concat(chunks, ignore_index=True, copy=False)
                del chunks  # Liberar memoria
                gc.collect()
            except Exception as e:
                st.error(f"Error al concatenar chunks: {str(e)}")
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
            import traceback
            st.error(f"Error detallado: {traceback.format_exc()}")
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