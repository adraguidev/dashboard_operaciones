import streamlit as st
import pandas as pd
from utils.display_utils import render_table
from utils.downloads import download_table_as_excel, download_detailed_list
from utils.table_generator import generate_table_multiple_years, generate_table_single_year
from config.settings import INACTIVE_EVALUATORS
from config.constants import VULNERABILIDAD_EVALUATORS

def render_pending_reports_tab(data, selected_module):
    st.header("Dashboard de Pendientes")
    
    # Filtrar pendientes sin asignar
    unassigned_data = data[(data['Evaluado'] == 'NO') & (data['EVALASIGN'].isna())]
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

    # Determinar evaluadores inactivos según el módulo
    module_inactive_evaluators = get_module_inactive_evaluators(selected_module)

    # Obtener todos los evaluadores del módulo actual
    all_evaluators = sorted(data['EVALASIGN'].dropna().unique())

    # Selección de vista
    view_option = st.radio(
        "Elige qué evaluadores deseas visualizar:",
        options=["Activos", "Inactivos", "Vulnerabilidad", "Total"],
        index=0
    )

    # Filtrar evaluadores según la opción seleccionada
    evaluators = filter_evaluators_by_view(
        view_option,
        all_evaluators,
        module_inactive_evaluators
    )

    if not evaluators:
        st.warning(f"No hay evaluadores en la categoría '{view_option}' para este módulo.")
        return

    # Mostrar filtro de evaluadores
    selected_evaluators = show_evaluator_filter(evaluators, selected_module, view_option)

    # Selección de años
    selected_years = st.multiselect(
        "Selecciona los Años",
        options=sorted(data['Anio'].unique())
    )

    # Mostrar tabla y descargas si se seleccionan años
    if selected_years:
        display_pending_reports(
            data, 
            selected_years, 
            selected_evaluators, 
            view_option
        )

def get_module_inactive_evaluators(selected_module):
    """Obtener evaluadores inactivos para el módulo seleccionado."""
    if selected_module in ['CCM', 'CCM-ESP', 'CCM-LEY']:
        return INACTIVE_EVALUATORS.get('CCM', [])
    elif selected_module == 'PRR':
        return INACTIVE_EVALUATORS.get('PRR', [])
    return []

def filter_evaluators_by_view(view_option, all_evaluators, module_inactive_evaluators):
    """Filtrar evaluadores según la vista seleccionada."""
    if view_option == "Vulnerabilidad":
        return [e for e in all_evaluators if e in VULNERABILIDAD_EVALUATORS]
    elif view_option == "Activos":
        return [
            e for e in all_evaluators
            if e not in module_inactive_evaluators 
            and e not in VULNERABILIDAD_EVALUATORS
        ]
    elif view_option == "Inactivos":
        return [
            e for e in module_inactive_evaluators
            if e in all_evaluators 
            and e not in VULNERABILIDAD_EVALUATORS
        ]
    else:  # Total
        return all_evaluators

def show_evaluator_filter(evaluators, selected_module, view_option):
    """Mostrar filtro de selección de evaluadores."""
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
    
    return selected_evaluators

def display_pending_reports(data, selected_years, selected_evaluators, view_option):
    """Mostrar reportes de pendientes."""
    # Filtrar solo los pendientes
    filtered_data = data[data['Evaluado'] == 'NO']

    # Filtrar según los evaluadores seleccionados
    if selected_evaluators:
        filtered_data = filtered_data[filtered_data['EVALASIGN'].isin(selected_evaluators)]

    if len(selected_years) > 1:
        display_multiple_years_report(filtered_data, selected_years, selected_evaluators, view_option)
    else:
        display_single_year_report(filtered_data, selected_years[0], selected_evaluators, view_option)

def display_multiple_years_report(filtered_data, selected_years, selected_evaluators, view_option):
    """Mostrar reporte para múltiples años."""
    table = generate_table_multiple_years(filtered_data, selected_years, selected_evaluators)
    total_pendientes = table['Total'].sum()
    st.metric("Total de Expedientes Pendientes", total_pendientes)
    render_table(table, f"Pendientes por Evaluador ({view_option}, Varios Años)")

    # Descarga como Excel
    excel_buf = download_table_as_excel(table, f"Pendientes_{view_option}_Varios_Años")
    st.download_button(
        "Descargar como Excel",
        excel_buf,
        file_name=f"pendientes_{view_option.lower()}_varios_anos.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def display_single_year_report(filtered_data, selected_year, selected_evaluators, view_option):
    """Mostrar reporte para un solo año."""
    table = generate_table_single_year(filtered_data, selected_year, selected_evaluators)
    total_pendientes = table['Total'].sum()
    st.metric("Total de Expedientes Pendientes", total_pendientes)
    render_table(table, f"Pendientes por Evaluador ({view_option}, Año {selected_year})")

    # Descarga como Excel
    excel_buf = download_table_as_excel(table, f"Pendientes_{view_option}_Año_{selected_year}")
    st.download_button(
        "Descargar como Excel",
        excel_buf,
        file_name=f"pendientes_{view_option.lower()}_año_{selected_year}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Descarga Detallada
    filters = {
        'Anio': [selected_year],
        'EVALASIGN': selected_evaluators if selected_evaluators else None
    }
    detailed_buf = download_detailed_list(filtered_data, filters)
    st.download_button(
        "Descargar Detallado (Pendientes - Todos los Filtros)",
        detailed_buf,
        file_name=f"pendientes_detallado_{view_option.lower()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )