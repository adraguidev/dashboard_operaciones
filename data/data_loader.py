import pandas as pd
import os
from config.settings import MODULE_FOLDERS
import streamlit as st
from .data_processor import process_date_columns, validate_data_integrity

@st.cache_data
def load_consolidated_cached(module_name):
    """
    Cargar datos consolidados del módulo con caché de Streamlit.
    """
    try:
        folder = MODULE_FOLDERS[module_name]
        file_path = find_consolidated_file(folder, module_name)
        
        if file_path:
            data = pd.read_excel(file_path)
            data = process_loaded_data(data)
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
    # Procesar columnas de fecha
    data = process_date_columns(data)
    
    # Convertir tipos de datos
    if 'Anio' in data.columns:
        data['Anio'] = data['Anio'].astype(int)
    if 'Mes' in data.columns:
        data['Mes'] = data['Mes'].astype(int)
    
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
        # Filtrar CCM-LEY
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