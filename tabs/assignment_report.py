import streamlit as st
import pandas as pd
import plotly.express as px

def render_assignment_report_tab(data: pd.DataFrame):
    try:
        st.header("Reporte de Asignaciones")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que no hay valores None en las columnas críticas
        data['EVALASIGN'] = data['EVALASIGN'].fillna('')
        data['FechaAsignacion'] = pd.to_datetime(data['FechaAsignacion'], errors='coerce')
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')
        
        # Filtrar datos nulos
        data = data.dropna(subset=['FechaExpendiente'])

        # Información de asignaciones de los últimos 15 días
        st.subheader("Porcentaje de Expedientes Asignados y Sin Asignar por Día (Últimos 15 Días)")
        
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

        # Calcular porcentajes y asegurar que no hay divisiones por cero
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
        return pd.DataFrame()  # Retornar DataFrame vacío en caso de error

def display_assignment_data(assignment_data):
    """Mostrar tabla de datos de asignación."""
    try:
        if not assignment_data.empty:
            st.dataframe(
                assignment_data[[
                    'FechaExpendiente', 'TotalExpedientes', 
                    'CantidadAsignados', 'CantidadSinAsignar', 
                    '% Sin Asignar'
                ]]
            )
        else:
            st.warning("No hay datos de asignación para mostrar")

    except Exception as e:
        st.error(f"Error al mostrar datos de asignación: {str(e)}")

def display_stacked_bar_chart(assignment_data):
    """Mostrar gráfico de barras apiladas de asignaciones."""
    try:
        if not assignment_data.empty:
            fig_stacked_bar = px.bar(
                assignment_data,
                x='FechaExpendiente',
                y=['CantidadAsignados', 'CantidadSinAsignar'],
                title="Distribución de Expedientes Asignados y Sin Asignar (Últimos 15 Días)",
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

            fig_stacked_bar.update_layout(
                barmode='stack',
                xaxis_title='Fecha Expediente',
                yaxis_title='Cantidad de Expedientes',
                legend_title='Estado'
            )

            st.plotly_chart(fig_stacked_bar)
        else:
            st.warning("No hay datos suficientes para mostrar el gráfico")

    except Exception as e:
        st.error(f"Error al mostrar el gráfico: {str(e)}") 