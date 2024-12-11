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

            # Optimizar la consulta inicial para reducir el uso de memoria
            pipeline = [
                {
                    "$project": {
                        "_id": 0,
                        "NumeroTramite": 1,
                        "EVALASIGN": 1,
                        "Anio": 1,
                        "Mes": 1,
                        "FechaExpendiente": 1,
                        "FECHA DE TRABAJO": 1,
                        "Evaluado": 1
                    }
                }
            ]
            
            # Usar cursor para procesar en chunks
            cursor = _self.migraciones_db[collection_name].aggregate(pipeline, allowDiskUse=True)
            
            chunks = []
            chunk_size = 10000
            current_chunk = []
            
            for doc in cursor:
                current_chunk.append(doc)
                if len(current_chunk) >= chunk_size:
                    chunks.append(pd.DataFrame(current_chunk))
                    current_chunk = []
            
            if current_chunk:
                chunks.append(pd.DataFrame(current_chunk))
            
            if not chunks:
                return None
            
            data = pd.concat(chunks, ignore_index=True)
            
            # Optimizar tipos de datos inmediatamente
            if 'Anio' in data.columns:
                data['Anio'] = pd.to_numeric(data['Anio'], downcast='integer')
            if 'Mes' in data.columns:
                data['Mes'] = pd.to_numeric(data['Mes'], downcast='integer')
            if 'EVALASIGN' in data.columns:
                data['EVALASIGN'] = data['EVALASIGN'].astype('category')
            
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