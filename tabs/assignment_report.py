import streamlit as st
import pandas as pd
import plotly.express as px

def render_assignment_report_tab(data):
    st.header("Porcentaje de Expedientes Asignados y Sin Asignar")
    
    # Información de asignaciones de los últimos 15 días
    st.subheader("Porcentaje de Expedientes Asignados y Sin Asignar por Día (Últimos 15 Días)")
    
    # Procesar y mostrar datos de asignación
    assignment_data = process_assignment_data(data)
    display_assignment_data(assignment_data)
    
    # Mostrar gráfico de barras apiladas
    display_stacked_bar_chart(assignment_data)

def process_assignment_data(data):
    """Procesar datos de asignación de los últimos 15 días."""
    # Filtrar datos recientes y excluir toma de imágenes
    last_15_days = pd.Timestamp.now() - pd.DateOffset(days=15)
    recent_data = data[
        (data['FechaExpendiente'] >= last_15_days) & 
        (data['UltimaEtapa'] != 'TOMA DE IMAGENES - I') & 
        (data['UltimaEtapa'] != 'TOMA DE IMAGENES - F')
    ]

    # Agrupar y calcular métricas
    assignment_data = recent_data.groupby('FechaExpendiente').apply(
        lambda x: pd.Series({
            'TotalExpedientes': len(x),
            'CantidadAsignados': len(x[x['EVALASIGN'].notna()]),
            'CantidadSinAsignar': len(x[x['EVALASIGN'].isna()])
        })
    ).reset_index()

    # Calcular porcentajes
    assignment_data['% Sin Asignar'] = (
        assignment_data['CantidadSinAsignar'] / assignment_data['TotalExpedientes']
    ) * 100

    # Formatear fechas y porcentajes
    assignment_data['FechaExpendiente'] = assignment_data['FechaExpendiente'].dt.strftime('%d/%m/%Y')
    assignment_data['% Sin Asignar'] = assignment_data['% Sin Asignar'].apply(lambda x: f"{x:.2f}%")

    return assignment_data

def display_assignment_data(assignment_data):
    """Mostrar tabla de datos de asignación."""
    st.dataframe(
        assignment_data[[
            'FechaExpendiente', 'TotalExpedientes', 
            'CantidadAsignados', 'CantidadSinAsignar', 
            '% Sin Asignar'
        ]]
    )

def display_stacked_bar_chart(assignment_data):
    """Mostrar gráfico de barras apiladas de asignaciones."""
    fig_stacked_bar = px.bar(
        assignment_data,
        x='FechaExpendiente',
        y=['CantidadAsignados', 'CantidadSinAsignar'],
        title="Distribución de Expedientes Asignados y Sin Asignar (Últimos 15 Días, Excluyendo 'TOMA DE IMAGENES - I')",
        labels={
            'value': 'Cantidad de Expedientes',
            'FechaExpendiente': 'Fecha Expediente',
            'variable': 'Estado'
        },
        text_auto=True,
        color_discrete_map={
            'CantidadAsignados': 'green',
            'CantidadSinAsignar': 'red'
        }
    )

    # Configurar diseño del gráfico
    fig_stacked_bar.update_layout(
        barmode='stack',
        xaxis_title='Fecha Expediente',
        yaxis_title='Cantidad de Expedientes',
        legend_title='Estado'
    )

    st.plotly_chart(fig_stacked_bar) 