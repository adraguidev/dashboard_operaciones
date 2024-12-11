import pandas as pd
import os
from config.settings import MODULE_FOLDERS
import streamlit as st
from .data_processor import process_date_columns, validate_data_integrity
import hashlib
from datetime import datetime

def get_file_hash(file_path):
    """
    Obtiene el hash del archivo y su última fecha de modificación.
    """
    if not os.path.exists(file_path):
        return None
    
    # Obtener timestamp de última modificación
    mod_time = os.path.getmtime(file_path)
    
    # Calcular hash del archivo
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
            
    return f"{hash_md5.hexdigest()}_{mod_time}"

@st.cache_data(hash_funcs={str: get_file_hash})
def load_consolidated_cached(module_name):
    """
    Cargar datos consolidados del módulo con caché basado en hash del archivo.
    """
    try:
        folder = MODULE_FOLDERS[module_name]
        file_path = find_consolidated_file(folder, module_name)
        
        if file_path:
            # El hash del archivo se usa como parte de la clave de caché
            file_hash = get_file_hash(file_path)
            
            data = pd.read_excel(
                file_path,
                engine='openpyxl',
                dtype_backend='pyarrow'
            )
            data = process_loaded_data(data)
            
            # Agregar metadata sobre la carga
            st.session_state[f'last_load_{module_name}'] = {
                'timestamp': datetime.now(),
                'file_hash': file_hash
            }
            
            return data
            
        return None
    except Exception as e:
        st.error(f"Error al cargar datos del módulo {module_name}: {str(e)}")
        return None

def find_consolidated_file(folder, module_name):
    """
    Encontrar archivo consolidado en la carpeta del módulo.
    """
    if not os.path.exists(folder):
        return None
        
    for file in os.listdir(folder):
        if file.startswith(f"Consolidado_{module_name}_CRUZADO") and file.endswith(".xlsx"):
            return os.path.join(folder, file)
    return None

def process_loaded_data(data):
    """
    Procesar datos cargados aplicando transformaciones necesarias.
    """
    with st.spinner('Procesando datos...'):
        # Procesar columnas de fecha
        data = process_date_columns(data)
        
        # Convertir tipos de datos
        if 'Anio' in data.columns:
            data['Anio'] = pd.to_numeric(data['Anio'], downcast='integer')
        if 'Mes' in data.columns:
            data['Mes'] = pd.to_numeric(data['Mes'], downcast='integer')
        
        # Validar integridad
        validation_results = validate_data_integrity(data)
        
        # Mostrar advertencias si hay problemas
        if validation_results['missing_dates'] > 0:
            st.warning(f"Hay {validation_results['missing_dates']} registros con fechas faltantes")
        if validation_results['invalid_dates'] > 0:
            st.warning(f"Hay {validation_results['invalid_dates']} registros con fechas inválidas")
        
        return data

def load_ccm_ley_data():
    """
    Cargar datos específicos para CCM-LEY.
    """
    ccm_data = load_consolidated_cached('CCM')
    ccm_esp_data = load_consolidated_cached('CCM-ESP')
    
    if ccm_data is not None and ccm_esp_data is not None:
        # Filtrar CCM-LEY: registros de CCM que no están en CCM-ESP
        ccm_ley_data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
        return process_loaded_data(ccm_ley_data)
    
    return None

def load_spe_data():
    """
    Cargar datos específicos para SPE.
    """
    folder = "descargas/SPE"
    file_path = os.path.join(folder, "MATRIZ.xlsx")
    
    if os.path.exists(file_path):
        try:
            data = pd.read_excel(file_path)
            return process_loaded_data(data)
        except Exception as e:
            st.error(f"Error al leer MATRIZ.xlsx: {str(e)}")
    
    return None 