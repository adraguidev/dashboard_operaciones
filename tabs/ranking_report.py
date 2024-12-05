import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from config.settings import MONGODB_CONFIG

def render_ranking_report_tab(data: pd.DataFrame, selected_module: str, rankings_collection):
    try:
        st.header("Ranking de Expedientes Trabajados")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que las fechas son válidas
        data['FECHA DE TRABAJO'] = pd.to_datetime(data['FECHA DE TRABAJO'], errors='coerce')
        
        # Filtrar datos nulos
        data = data.dropna(subset=['FECHA DE TRABAJO', 'EVALASIGN'])

        # Resto del código...
    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")

def get_last_date_from_db(module, collection):
    """Obtener la última fecha registrada para el módulo."""
    ultimo_registro = collection.find_one(
        {"modulo": module}, 
        sort=[("fecha", -1)]
    )
    if ultimo_registro and 'fecha' in ultimo_registro:
        return pd.to_datetime(ultimo_registro['fecha'])
    return None

def prepare_inconsistencias_dataframe(datos_validos):
    """Prepara el DataFrame de inconsistencias para su visualización."""
    # Filtrar y crear una copia única al inicio
    mask = datos_validos['DiferenciaDias'] > 2
    columnas = ['NumeroTramite', 'EVALASIGN', 'FECHA DE TRABAJO', 'FechaPre', 'DiferenciaDias', 'ESTADO', 'DESCRIPCION']
    df = datos_validos.loc[mask, columnas].copy()
    
    if not df.empty:
        # Formatear fechas y tipos de datos
        df.loc[:, 'FECHA DE TRABAJO'] = df['FECHA DE TRABAJO'].dt.strftime('%Y-%m-%d')
        df.loc[:, 'FechaPre'] = df['FechaPre'].dt.strftime('%Y-%m-%d')
        df.loc[:, 'DiferenciaDias'] = df['DiferenciaDias'].astype(int)
        df.loc[:, 'DESCRIPCION'] = df['DESCRIPCION'].astype(str)
        
        # Renombrar columnas
        new_columns = {
            'NumeroTramite': 'N° Expediente',
            'EVALASIGN': 'Evaluador',
            'FECHA DE TRABAJO': 'Fecha de Trabajo',
            'FechaPre': 'Fecha Pre',
            'DiferenciaDias': 'Diferencia en Días',
            'ESTADO': 'Estado',
            'DESCRIPCION': 'Descripción'
        }
        df = df.rename(columns=new_columns)
        
        # Ordenar por diferencia de días
        df = df.sort_values('Diferencia en Días', ascending=False)
    
    return df 