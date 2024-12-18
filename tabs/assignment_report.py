import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

def render_assignment_report_tab(data: pd.DataFrame):
    try:
        st.header("📋 Reporte de Asignaciones")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que no hay valores None en las columnas críticas
        data['EVALASIGN'] = data['EVALASIGN'].fillna('')
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')

        # Información de asignaciones de los últimos 15 días
        st.subheader("📊 Porcentaje de Expedientes Asignados y Sin Asignar por Día")
        
        # Procesar y mostrar datos de asignación
        assignment_data = process_assignment_data(data)
        display_assignment_data(assignment_data)
        
        # Mostrar gráfico de barras apiladas
        display_stacked_bar_chart(assignment_data)

    except Exception as e:
        st.error(f"Error al procesar el reporte de asignaciones: {str(e)}")
        print(f"Error detallado: {str(e)}")

def process_assignment_data(data):
    """Procesar datos de asignación de los últimos 15 días."""
    try:
        # Filtrar datos recientes
        last_15_days = pd.Timestamp.now() - pd.DateOffset(days=15)
        recent_data = data[data['FechaExpendiente'] >= last_15_days]

        # Agrupar y calcular métricas
        assignment_data = recent_data.groupby('FechaExpendiente').apply(
            lambda x: pd.Series({
                'TotalExpedientes': len(x),
                'CantidadAsignados': len(x[x['EVALASIGN'] != '']),
                'CantidadSinAsignar': len(x[x['EVALASIGN'] == ''])
            })
        ).reset_index()

        # Calcular porcentajes
        assignment_data['% Sin Asignar'] = assignment_data.apply(
            lambda row: f"{(row['CantidadSinAsignar'] / row['TotalExpedientes'] * 100):.2f}%" 
            if row['TotalExpedientes'] > 0 else "0.00%",
            axis=1
        )

        # Formatear fechas
        assignment_data['FechaExpendiente'] = assignment_data['FechaExpendiente'].dt.strftime('%d/%m/%Y')

        return assignment_data

    except Exception as e:
        st.error(f"Error al procesar datos de asignación: {str(e)}")
        print(f"Error detallado en process_assignment_data: {str(e)}")
        return pd.DataFrame()

def display_assignment_data(assignment_data):
    """Mostrar tabla de datos de asignación."""
    try:
        if not assignment_data.empty:
            st.dataframe(
                assignment_data[[
                    'FechaExpendiente', 'TotalExpedientes', 
                    'CantidadAsignados', 'CantidadSinAsignar', 
                    '% Sin Asignar'
                ]],
                use_container_width=True,
                column_config={
                    'FechaExpendiente': 'Fecha',
                    'TotalExpedientes': 'Total',
                    'CantidadAsignados': 'Asignados',
                    'CantidadSinAsignar': 'Sin Asignar',
                    '% Sin Asignar': 'Porcentaje Sin Asignar'
                }
            )
        else:
            st.warning("No hay datos de asignación para mostrar")

    except Exception as e:
        st.error(f"Error al mostrar datos de asignación: {str(e)}")

def display_stacked_bar_chart(assignment_data):
    """Mostrar gráfico de barras apiladas de asignaciones."""
    try:
        if not assignment_data.empty:
            fig = px.bar(
                assignment_data,
                x='FechaExpendiente',
                y=['CantidadAsignados', 'CantidadSinAsignar'],
                title="Distribución de Expedientes Asignados y Sin Asignar (Últimos 15 Días)",
                labels={
                    'value': 'Cantidad de Expedientes',
                    'FechaExpendiente': 'Fecha',
                    'variable': 'Estado'
                },
                text_auto=True,
                color_discrete_map={
                    'CantidadAsignados': '#2ecc71',  # Verde
                    'CantidadSinAsignar': '#e74c3c'  # Rojo
                }
            )

            fig.update_layout(
                barmode='stack',
                xaxis_title='Fecha',
                yaxis_title='Cantidad de Expedientes',
                legend_title='Estado',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar métricas resumen
            total_asignados = assignment_data['CantidadAsignados'].sum()
            total_sin_asignar = assignment_data['CantidadSinAsignar'].sum()
            total_expedientes = total_asignados + total_sin_asignar
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Expedientes", f"{total_expedientes:,d}")
            col2.metric("Total Asignados", f"{total_asignados:,d}")
            col3.metric(
                "Sin Asignar", 
                f"{total_sin_asignar:,d}",
                f"{(total_sin_asignar/total_expedientes*100):.1f}%"
            )
        else:
            st.warning("No hay datos suficientes para mostrar el gráfico")

    except Exception as e:
        st.error(f"Error al mostrar el gráfico: {str(e)}") 