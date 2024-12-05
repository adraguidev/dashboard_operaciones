import streamlit as st
import pandas as pd
import plotly.express as px
from utils.downloads import download_table_as_excel
from config.settings import INACTIVE_EVALUATORS

def render_pending_reports_tab(data: pd.DataFrame, selected_module: str):
    st.header("Reporte de Pendientes")

    # Filtros superiores
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Selector de vista
        view_type = st.radio(
            "Seleccionar Vista",
            ["Activos", "Inactivos", "Vulnerabilidad", "Total"],
            horizontal=True
        )
    
    with col2:
        # Selector de años múltiple
        available_years = sorted(data['Anio'].unique(), reverse=True)
        selected_years = st.multiselect(
            "Seleccionar Año(s)",
            options=available_years,
            default=[max(available_years)]
        )
    
    if not selected_years:
        st.warning("Por favor seleccione al menos un año")
        return

    # Filtrar datos por años seleccionados y pendientes
    filtered_data = data[
        (data['Anio'].isin(selected_years)) &
        (data['EVALUADO'] == 'NO')
    ].copy()

    # Aplicar filtros según la vista seleccionada
    if view_type == "Activos":
        filtered_data = filtered_data[
            ~filtered_data['EVALASIGN'].isin(INACTIVE_EVALUATORS.get(selected_module, []))
        ]
    elif view_type == "Inactivos":
        filtered_data = filtered_data[
            filtered_data['EVALASIGN'].isin(INACTIVE_EVALUATORS.get(selected_module, []))
        ]
    elif view_type == "Vulnerabilidad":
        filtered_data = filtered_data[
            filtered_data['EVALASIGN'] == 'VULNERABILIDAD'
        ]

    # Si no hay datos después del filtrado
    if filtered_data.empty:
        st.info("No se encontraron expedientes pendientes con los filtros seleccionados")
        return

    # Preparar datos para la tabla
    if len(selected_years) == 1:
        # Vista por meses para un solo año
        pending_table = filtered_data.groupby(['EVALASIGN', 'Mes']).agg({
            'NumeroTramite': 'count'
        }).reset_index()
        
        # Pivot para mostrar meses como columnas
        pending_table = pending_table.pivot(
            index='EVALASIGN',
            columns='Mes',
            values='NumeroTramite'
        ).fillna(0)
        
        # Agregar total
        pending_table['TOTAL'] = pending_table.sum(axis=1)
        
        # Ordenar por total descendente
        pending_table = pending_table.sort_values('TOTAL', ascending=False)
        
    else:
        # Vista por años cuando hay múltiples años seleccionados
        pending_table = filtered_data.groupby(['EVALASIGN', 'Anio']).agg({
            'NumeroTramite': 'count'
        }).reset_index()
        
        pending_table = pending_table.pivot(
            index='EVALASIGN',
            columns='Anio',
            values='NumeroTramite'
        ).fillna(0)
        
        # Agregar total
        pending_table['TOTAL'] = pending_table.sum(axis=1)
        
        # Ordenar por total descendente
        pending_table = pending_table.sort_values('TOTAL', ascending=False)

    # Convertir números a enteros
    pending_table = pending_table.astype(int)

    # Mostrar tabla
    st.dataframe(
        pending_table,
        use_container_width=True,
        height=400,
        column_config={
            col: st.column_config.NumberColumn(
                col,
                format="%d",
                width="small"
            ) for col in pending_table.columns
        }
    )

    # Botón de descarga
    excel_data = pending_table.reset_index()
    excel_buffer = download_table_as_excel(excel_data, f"Pendientes_{selected_module}")
    
    st.download_button(
        label=" Descargar Reporte",
        data=excel_buffer,
        file_name=f"Pendientes_{selected_module}_{'-'.join(map(str, selected_years))}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Mostrar totales
    total_pendientes = pending_table['TOTAL'].sum()
    st.metric("Total de Expedientes Pendientes", f"{total_pendientes:,d}")