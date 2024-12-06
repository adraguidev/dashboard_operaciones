import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

def render_closing_analysis_tab(data: pd.DataFrame, module_name: str = None):
    try:
        st.header("🔒 Análisis de Cierre de Expedientes")
        
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Lógica específica para el módulo SOL
        if module_name == 'SOL':
            render_sol_closing_analysis(data)
            return

        # Convertir y validar fechas
        data['FECHA DE TRABAJO'] = pd.to_datetime(data['FECHA DE TRABAJO'], errors='coerce')
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')

        # Calcular tiempo de cierre
        data['TiempoCierre'] = (data['FECHA DE TRABAJO'] - data['FechaExpendiente']).dt.total_seconds() / (24 * 60 * 60)

        # Filtrar últimos 15 días y expedientes cerrados
        fecha_actual = datetime.now()
        fecha_inicio = fecha_actual - timedelta(days=15)
        
        expedientes_cerrados = data[
            (data['FECHA DE TRABAJO'] >= fecha_inicio) &
            (data['FECHA DE TRABAJO'] <= fecha_actual) &
            (data['TiempoCierre'] >= 0)
        ].copy()

        if expedientes_cerrados.empty:
            st.warning("No se encontraron expedientes cerrados en los últimos 15 días")
            return

        # Mostrar estadísticas generales
        st.subheader("📊 Estadísticas Generales de Cierre")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tiempo_promedio = expedientes_cerrados['TiempoCierre'].mean()
            st.metric(
                "Tiempo Promedio de Cierre",
                f"{tiempo_promedio:.1f} días"
            )
        
        with col2:
            tiempo_mediano = expedientes_cerrados['TiempoCierre'].median()
            st.metric(
                "Tiempo Mediano de Cierre",
                f"{tiempo_mediano:.1f} días"
            )
        
        with col3:
            total_cerrados = len(expedientes_cerrados)
            st.metric(
                "Total Expedientes Cerrados",
                f"{total_cerrados:,d}"
            )

        # Top 25 expedientes con mayor tiempo de cierre
        st.subheader("📈 Top 25 Expedientes con Mayor Tiempo de Cierre (Últimos 15 días)")
        
        top_25 = expedientes_cerrados.nlargest(25, 'TiempoCierre')[[
            'NumeroTramite',
            'FechaExpendiente',
            'FECHA DE TRABAJO',
            'TiempoCierre',
            'EVALASIGN',
            'ESTADO',
            'UltimaEtapa'
        ]].copy()

        # Formatear fechas y números
        top_25['FechaExpendiente'] = top_25['FechaExpendiente'].dt.strftime('%d/%m/%Y')
        top_25['FECHA DE TRABAJO'] = top_25['FECHA DE TRABAJO'].dt.strftime('%d/%m/%Y')
        top_25['TiempoCierre'] = top_25['TiempoCierre'].round(1)

        # Mostrar tabla
        st.dataframe(
            top_25,
            use_container_width=True,
            column_config={
                'NumeroTramite': 'Expediente',
                'FechaExpendiente': 'Fecha Ingreso',
                'FECHA DE TRABAJO': 'Fecha Cierre',
                'TiempoCierre': st.column_config.NumberColumn(
                    'Tiempo de Cierre (días)',
                    format="%.1f"
                ),
                'EVALASIGN': 'Evaluador',
                'ESTADO': 'Estado',
                'UltimaEtapa': 'Última Etapa'
            }
        )

        # Gráfico de distribución
        st.subheader("📊 Distribución de Tiempos de Cierre")
        fig = px.histogram(
            expedientes_cerrados,
            x='TiempoCierre',
            nbins=50,
            title='Distribución de Tiempos de Cierre',
            labels={'TiempoCierre': 'Tiempo de Cierre (días)', 'count': 'Cantidad de Expedientes'}
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar la pestaña de cierre de expedientes: {str(e)}")
        print(f"Error detallado: {str(e)}")

def render_sol_closing_analysis(data: pd.DataFrame):
    """Renderiza el análisis de cierre específico para el módulo SOL."""
    try:
        # Convertir fechas
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], format='%d/%m/%Y', errors='coerce')
        data['FechaPre'] = pd.to_datetime(
            data['FechaPre'], 
            format='%d/%m/%Y', 
            errors='coerce'
        )

        # Calcular tiempo de cierre en días
        data['TiempoCierre'] = (
            data['FechaPre'] - data['FechaExpendiente']
        ).dt.total_seconds() / (24 * 60 * 60)  # Convertir a días

        # Filtrar expedientes cerrados (con fecha de pre)
        expedientes_cerrados = data[
            data['FechaPre'].notna() &
            (data['TiempoCierre'] >= 0)  # Evitar tiempos negativos
        ].copy()

        if expedientes_cerrados.empty:
            st.warning("No se encontraron expedientes cerrados para analizar")
            return

        # Mostrar estadísticas generales
        st.subheader("📊 Estadísticas Generales de Cierre")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tiempo_promedio = expedientes_cerrados['TiempoCierre'].mean()
            st.metric(
                "Tiempo Promedio de Cierre",
                f"{tiempo_promedio:.1f} días"
            )
        
        with col2:
            tiempo_mediano = expedientes_cerrados['TiempoCierre'].median()
            st.metric(
                "Tiempo Mediano de Cierre",
                f"{tiempo_mediano:.1f} días"
            )
        
        with col3:
            total_cerrados = len(expedientes_cerrados)
            st.metric(
                "Total Expedientes Cerrados",
                f"{total_cerrados:,d}"
            )

        # Top 25 expedientes con mayor tiempo de cierre
        st.subheader("📈 Top 25 Expedientes con Mayor Tiempo de Cierre")
        
        # Ordenar por tiempo de cierre descendente y tomar los primeros 25
        top_25 = expedientes_cerrados.nlargest(25, 'TiempoCierre')[[
            'NumeroTramite',
            'Dependencia',
            'FechaExpendiente',
            'FechaPre',
            'TiempoCierre',
            'EstadoTramite',
            'UltimaEtapa',
            'EstadoPre'  # Agregado EstadoPre
        ]].copy()

        # Formatear fechas para visualización
        top_25['FechaExpendiente'] = top_25['FechaExpendiente'].dt.strftime('%d/%m/%Y')
        top_25['FechaPre'] = top_25['FechaPre'].dt.strftime('%d/%m/%Y')
        top_25['TiempoCierre'] = top_25['TiempoCierre'].round(1)

        # Mostrar tabla
        st.dataframe(
            top_25,
            use_container_width=True,
            column_config={
                'NumeroTramite': 'Expediente',
                'Dependencia': 'Dependencia',
                'FechaExpendiente': 'Fecha Ingreso',
                'FechaPre': 'Fecha Pre',
                'TiempoCierre': st.column_config.NumberColumn(
                    'Tiempo de Cierre (días)',
                    format="%.1f"
                ),
                'EstadoTramite': 'Estado Trámite',
                'EstadoPre': 'Estado Pre',
                'UltimaEtapa': 'Última Etapa'
            }
        )

        # Gráfico de distribución de tiempos de cierre
        st.subheader("📊 Distribución de Tiempos de Cierre")
        fig = px.histogram(
            expedientes_cerrados,
            x='TiempoCierre',
            nbins=50,
            title='Distribución de Tiempos de Cierre',
            labels={'TiempoCierre': 'Tiempo de Cierre (días)', 'count': 'Cantidad de Expedientes'}
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar el análisis de cierre SOL: {str(e)}")
        print(f"Error detallado: {str(e)}") 