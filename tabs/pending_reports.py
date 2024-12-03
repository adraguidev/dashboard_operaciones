import streamlit as st
import pandas as pd
from utils.display_utils import render_table
from utils.downloads import download_table_as_excel, download_detailed_list
from utils.table_generator import generate_table_multiple_years, generate_table_single_year
from config.settings import INACTIVE_EVALUATORS
from config.constants import VULNERABILIDAD_EVALUATORS

def render_pending_reports_tab(data, selected_module):
    """Renderizar pestaña de reportes pendientes."""
    st.header("Dashboard de Pendientes")
    
    # Filtrar solo los pendientes
    data = data[data['Evaluado'] == 'NO']
    
    # Filtrar pendientes sin asignar
    unassigned_data = data[data['EVALASIGN'].isna()]
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

    # Selección de vista (Activos, Inactivos, Total)
    st.subheader("Selecciona la Vista")
    view_option = st.radio(
        "Elige qué evaluadores deseas visualizar:",
        options=["Activos", "Inactivos", "Vulnerabilidad", "Total"],
        horizontal=True
    )

    # Obtener evaluadores según la vista seleccionada
    if view_option == "Activos":
        evaluators = get_active_evaluators(selected_module, data)
    elif view_option == "Inactivos":
        evaluators = INACTIVE_EVALUATORS.get(selected_module, [])
    elif view_option == "Vulnerabilidad":
        evaluators = VULNERABILIDAD_EVALUATORS.get(selected_module, [])
    else:  # Total
        evaluators = sorted(data['EVALASIGN'].dropna().unique())

    # Selección de años
    selected_years = st.multiselect(
        "Selecciona los Años",
        options=sorted(data['Anio'].unique())
    )

    # Mostrar filtro de evaluadores
    st.subheader(f"Evaluadores ({view_option})")
    selected_evaluators = []
    with st.expander(f"Filtro de Evaluadores ({view_option})", expanded=False):
        select_all = st.checkbox("Seleccionar Todos", value=True)
        if select_all:
            selected_evaluators = evaluators
        else:
            for evaluator in evaluators:
                if st.checkbox(evaluator, value=False, key=f"{selected_module}_checkbox_{evaluator}"):
                    selected_evaluators.append(evaluator)

    # Mostrar tabla y descargas si se seleccionan años
    if selected_years and selected_evaluators:
        display_multiple_years_report(data, selected_years, selected_evaluators)

def get_active_evaluators(selected_module, data):
    """Obtener evaluadores activos para el módulo seleccionado."""
    # Obtener todos los evaluadores del módulo actual
    all_evaluators = sorted(data['EVALASIGN'].dropna().unique())
    
    # Obtener inactivos y vulnerables
    module_inactive_evaluators = INACTIVE_EVALUATORS.get(selected_module, [])
    vulnerabilidad_evaluators = VULNERABILIDAD_EVALUATORS.get(selected_module, [])
    
    # Los evaluadores activos son aquellos que no están ni inactivos ni en vulnerabilidad
    return [
        e for e in all_evaluators 
        if e not in module_inactive_evaluators 
        and e not in vulnerabilidad_evaluators
    ]

def display_multiple_years_report(data, selected_years, selected_evaluators):
    """Mostrar reporte para múltiples años."""
    # Filtrar datos según años y evaluadores seleccionados
    filtered_data = data[
        (data['Anio'].isin(selected_years)) & 
        (data['EVALASIGN'].isin(selected_evaluators))
    ]
    
    table = generate_table_multiple_years(filtered_data, selected_years)
    total_pendientes = table['Total'].sum()
    st.metric("Total de Expedientes Pendientes", total_pendientes)
    render_table(table, "Pendientes por Evaluador")

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
        'EVALASIGN': selected_evaluators
    }
    detailed_buf = download_detailed_list(filtered_data, filters)
    st.download_button(
        "Descargar Detallado (Pendientes - Todos los Filtros)",
        detailed_buf,
        file_name="pendientes_detallado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )