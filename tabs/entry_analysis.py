import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

def render_entry_analysis_tab(data: pd.DataFrame):
    try:
        st.header("📊 Análisis de Ingreso de Expedientes")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que las fechas son válidas
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')
        data = data.dropna(subset=['FechaExpendiente'])

        # Tabla de ingresos diarios
        st.subheader("Detalle de Ingresos Diarios (Últimos 30 días)")
        
        # Preparar datos
        last_30_days = data[data['FechaExpendiente'] >= (pd.Timestamp.now() - pd.DateOffset(days=30))]
        daily_counts = last_30_days.groupby(last_30_days['FechaExpendiente'].dt.date).agg({
            'NumeroTramite': 'count',
            'ESTADO': lambda x: ', '.join(x.unique())
        }).reset_index()
        
        daily_counts.columns = ['Fecha', 'Total Ingresos', 'Estados']
        daily_counts['Fecha'] = daily_counts['Fecha'].dt.strftime('%d/%m/%Y')
        
        # Ordenar por fecha descendente
        daily_counts = daily_counts.sort_values('Fecha', ascending=False)
        
        # Agregar columna de promedio móvil de 7 días
        daily_counts['Promedio 7 días'] = daily_counts['Total Ingresos'].rolling(7, min_periods=1).mean().round(1)
        
        # Mostrar tabla con formato mejorado
        st.dataframe(
            daily_counts,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Fecha': st.column_config.TextColumn('Fecha', width='small'),
                'Total Ingresos': st.column_config.NumberColumn('Total Ingresos', format='%d'),
                'Promedio 7 días': st.column_config.NumberColumn('Promedio 7 días', format='%.1f'),
                'Estados': st.column_config.TextColumn('Estados', width='medium')
            }
        )

        # Mostrar estadísticas resumen
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Promedio diario", f"{daily_counts['Total Ingresos'].mean():.1f}")
        with col2:
            st.metric("Total del período", f"{daily_counts['Total Ingresos'].sum():,.0f}")
        with col3:
            st.metric("Días con registros", f"{len(daily_counts):,d}")

        # Gráfico de tendencia
        st.subheader("Tendencia de Ingresos")
        fig = go.Figure()
        
        # Línea de ingresos diarios
        fig.add_trace(go.Scatter(
            x=daily_counts['Fecha'],
            y=daily_counts['Total Ingresos'],
            name='Ingresos Diarios',
            mode='lines+markers'
        ))
        
        # Línea de promedio móvil
        fig.add_trace(go.Scatter(
            x=daily_counts['Fecha'],
            y=daily_counts['Promedio 7 días'],
            name='Promedio Móvil (7 días)',
            line=dict(dash='dash')
        ))
        
        fig.update_layout(
            title="Tendencia de Ingresos Diarios y Promedio Móvil",
            xaxis_title="Fecha",
            yaxis_title="Cantidad de Expedientes",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)

        # Análisis mensual y anual
        col1, col2 = st.columns(2)
        
        with col1:
            # Análisis mensual del año actual
            st.subheader(f"Ingresos Mensuales {datetime.now().year}")
            monthly_data = data[data['FechaExpendiente'].dt.year == datetime.now().year].groupby(
                data['FechaExpendiente'].dt.month
            ).size()
            
            month_names = {
                1:'Enero', 2:'Febrero', 3:'Marzo', 4:'Abril', 
                5:'Mayo', 6:'Junio', 7:'Julio', 8:'Agosto',
                9:'Septiembre', 10:'Octubre', 11:'Noviembre', 12:'Diciembre'
            }
            monthly_data.index = monthly_data.index.map(month_names)
            
            fig_monthly = px.bar(
                monthly_data,
                labels={'value': 'Cantidad de Expedientes', 'index': 'Mes'},
                title=f"Ingresos por Mes {datetime.now().year}"
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        with col2:
            # Análisis anual
            st.subheader("Ingresos Anuales")
            yearly_data = data.groupby(data['FechaExpendiente'].dt.year).size()
            fig_yearly = px.bar(
                yearly_data,
                labels={'value': 'Cantidad de Expedientes', 'index': 'Año'},
                title="Ingresos por Año"
            )
            st.plotly_chart(fig_yearly, use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        print(f"Error detallado: {str(e)}") 