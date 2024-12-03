import streamlit as st
import pandas as pd
from utils.display_utils import render_table
from utils.downloads import download_table_as_excel, download_detailed_list
from utils.table_generator import generate_table_multiple_years, generate_table_single_year
from config.settings import INACTIVE_EVALUATORS
from config.constants import VULNERABILIDAD_EVALUATORS

def render_pending_reports_tab(data, selected_module):
    """Renderizar pestaña de reportes pendientes."""
    # Obtener evaluadores según el módulo
    active_evaluators = get_active_evaluators(selected_module)
    inactive_evaluators = INACTIVE_EVALUATORS.get(selected_module, [])
    vulnerability_evaluators = get_vulnerability_evaluators(selected_module)
    
    # Crear selectbox para tipo de evaluadores
    evaluator_type = st.radio(
        "Elige qué evaluadores deseas visualizar:",
        ["Activos", "Inactivos", "Vulnerabilidad", "Total"],
        horizontal=True
    )
    
    # Filtrar datos según la selección
    if evaluator_type == "Activos":
        filtered_data = data[data['EVALASIGN'].isin(active_evaluators)]
    elif evaluator_type == "Inactivos":
        filtered_data = data[data['EVALASIGN'].isin(inactive_evaluators)]
    elif evaluator_type == "Vulnerabilidad":
        filtered_data = data[data['EVALASIGN'].isin(vulnerability_evaluators)]
    else:  # Total
        filtered_data = data.copy()
    
    # Mostrar datos filtrados
    display_pending_data(filtered_data)

def get_active_evaluators(selected_module):
    """Obtener evaluadores activos para el módulo seleccionado."""
    if selected_module in ['CCM', 'CCM-ESP', 'CCM-LEY']:
        return INACTIVE_EVALUATORS.get('CCM', [])
    elif selected_module == 'PRR':
        return INACTIVE_EVALUATORS.get('PRR', [])
    return []

def get_vulnerability_evaluators(selected_module):
    """Obtener evaluadores vulnerables para el módulo seleccionado."""
    if selected_module in ['CCM', 'CCM-ESP', 'CCM-LEY']:
        return VULNERABILIDAD_EVALUATORS.get('CCM', [])
    elif selected_module == 'PRR':
        return VULNERABILIDAD_EVALUATORS.get('PRR', [])
    return []

def display_pending_data(filtered_data):
    """Mostrar datos filtrados."""
    st.header("Dashboard de Pendientes")
    
    # Filtrar pendientes sin asignar
    unassigned_data = filtered_data[(filtered_data['Evaluado'] == 'NO') & (filtered_data['EVALASIGN'].isna())]
    total_unassigned = len(unassigned_data)

    if total_unassigned > 0:
        st.metric("Total de Pendientes Sin Asignar", total_unassigned)
        
        # Botón para descargar pendientes sin asignar
        unassigned_buf = download_table_as_excel(unassigned_data, "Pendientes_Sin_Asignar")
        st.download_button(
            label="Descargar Pendientes Sin Asignar",
            data=unassigned_buf,
            file_name="pendientes_sin_asignar.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No hay pendientes sin asignar en este momento.")

    # Selección de años
    selected_years = st.multiselect(
        "Selecciona los Años",
        options=sorted(filtered_data['Anio'].unique())
    )

    # Mostrar tabla y descargas si se seleccionan años
    if selected_years:
        display_multiple_years_report(filtered_data, selected_years)

def display_multiple_years_report(filtered_data, selected_years):
    """Mostrar reporte para múltiples años."""
    table = generate_table_multiple_years(filtered_data, selected_years)
    total_pendientes = table['Total'].sum()
    st.metric("Total de Expedientes Pendientes", total_pendientes)
    render_table(table, "Pendientes por Evaluador (Varios Años)")

    # Descarga como Excel
    excel_buf = download_table_as_excel(table, "Pendientes_Varios_Años")
    st.download_button(
        "Descargar como Excel",
        excel_buf,
        file_name="pendientes_varios_anos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Descarga Detallada
    filters = {
        'Anio': selected_years,
        'EVALASIGN': filtered_data['EVALASIGN'].dropna().unique()
    }
    detailed_buf = download_detailed_list(filtered_data, filters)
    st.download_button(
        "Descargar Detallado (Pendientes - Todos los Filtros)",
        detailed_buf,
        file_name="pendientes_detallado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )