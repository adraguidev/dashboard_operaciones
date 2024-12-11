import pandas as pd
import streamlit as st
from datetime import datetime
from pymongo import MongoClient
import os
from config.settings import MONGODB_COLLECTIONS, DATE_COLUMNS

class DataLoader:
    def __init__(_self):
        """Inicializa las conexiones a MongoDB usando los secrets de Streamlit."""
        try:
            _self.client = MongoClient(st.secrets["connections"]["mongodb"]["uri"])
            # Base de datos para datos consolidados
            _self.migraciones_db = _self.client['migraciones_db']
            # Base de datos para rankings
            _self.expedientes_db = _self.client['expedientes_db']
            # Verificar conexiones
            _self.migraciones_db.command('ping')
            _self.expedientes_db.command('ping')
        except Exception as e:
            st.error(f"Error al conectar con MongoDB: {str(e)}")
            raise

    @st.cache_data(ttl=3600)
    def load_module_data(_self, module_name: str) -> pd.DataFrame:
        """Carga datos consolidados desde migraciones_db."""
        try:
            # SPE usa Google Sheets
            if module_name == 'SPE':
                return _self._load_spe_from_sheets()
            
            # Procesamiento especial para CCM-LEY
            if module_name == 'CCM-LEY':
                # Cargar datos de CCM y CCM-ESP
                ccm_data = _self.load_module_data('CCM')
                ccm_esp_data = _self.load_module_data('CCM-ESP')
                
                if ccm_data is not None and ccm_esp_data is not None:
                    # Filtrar CCM-LEY: registros de CCM que no están en CCM-ESP
                    data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
                    
                    # Verificar si existe la columna TipoTramite y filtrar
                    if 'TipoTramite' in data.columns:
                        data = data[data['TipoTramite'] == 'LEY'].copy()
                    return data
                else:
                    st.error("No se pudieron cargar los datos necesarios para CCM-LEY")
                    return None

            collection_name = MONGODB_COLLECTIONS.get(module_name)
            if not collection_name:
                raise ValueError(f"Módulo no reconocido: {module_name}")

            # Optimizar la consulta para cargar solo los campos necesarios
            needed_fields = {
                "_id": 0,
                "NumeroTramite": 1,
                "EVALASIGN": 1,
                "Anio": 1,
                "Mes": 1,
                "FechaExpendiente": 1,
                "FECHA DE TRABAJO": 1,
                "Evaluado": 1,
                "ESTADO": 1,
                "UltimaEtapa": 1,
                "Dependencia": 1
            }

            # Usar cursor con batch_size para controlar el uso de memoria
            cursor = _self.migraciones_db[collection_name].find(
                {},
                needed_fields
            ).batch_size(5000)

            # Procesar en chunks más pequeños
            chunks = []
            current_chunk = []
            
            for doc in cursor:
                current_chunk.append(doc)
                if len(current_chunk) >= 5000:
                    df_chunk = pd.DataFrame(current_chunk)
                    # Optimizar tipos de datos inmediatamente
                    df_chunk = optimize_datatypes(df_chunk)
                    chunks.append(df_chunk)
                    current_chunk = []
            
            if current_chunk:
                df_chunk = pd.DataFrame(current_chunk)
                df_chunk = optimize_datatypes(df_chunk)
                chunks.append(df_chunk)

            if not chunks:
                return None

            # Concatenar chunks optimizados
            data = pd.concat(chunks, ignore_index=True)
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

def optimize_datatypes(df):
    """Optimiza los tipos de datos para reducir uso de memoria"""
    if df.empty:
        return df
        
    # Convertir strings a categorías si son repetitivos
    for col in df.select_dtypes(include=['object']):
        if df[col].nunique() / len(df) < 0.5:  # Si hay muchos valores repetidos
            df[col] = df[col].astype('category')
    
    # Optimizar tipos numéricos
    for col in df.select_dtypes(include=['int64']):
        df[col] = pd.to_numeric(df[col], downcast='integer')
    
    for col in df.select_dtypes(include=['float64']):
        df[col] = pd.to_numeric(df[col], downcast='float')
    
    return df