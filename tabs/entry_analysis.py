import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import numpy as np
from datetime import datetime, timedelta

def render_entry_analysis_tab(data: pd.DataFrame):
    try:
        st.header("📊 Análisis y Predicción de Ingresos")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que las fechas son válidas
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')
        data = data.dropna(subset=['FechaExpendiente'])

        # Layout principal con dos columnas
        col1, col2 = st.columns([2, 1])

        with col1:
            render_prediction_chart(data)
        
        with col2:
            render_key_metrics(data)

        # Análisis temporal debajo
        st.markdown("---")
        render_temporal_insights(data)
        
        # Patrones y anomalías
        st.markdown("---")
        render_patterns_analysis(data)

def render_prediction_chart(data):
    """Renderiza gráfico principal de predicción"""
    daily_counts = data.groupby(data['FechaExpendiente'].dt.date).size().reset_index(name='Ingresos')
    daily_counts['FechaExpendiente'] = pd.to_datetime(daily_counts['FechaExpendiente'])
    
    # Modelo de predicción polinomial
    X = np.arange(len(daily_counts)).reshape(-1, 1)
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    
    model = LinearRegression()
    model.fit(X_poly, daily_counts['Ingresos'])
    
    # Predicción 30 días
    future_dates = pd.date_range(
        start=daily_counts['FechaExpendiente'].max(), 
        periods=31, 
        freq='D'
    )[1:]
    
    X_future = np.arange(len(daily_counts), len(daily_counts) + 30).reshape(-1, 1)
    X_future_poly = poly.transform(X_future)
    predictions = model.predict(X_future_poly)
    
    fig = go.Figure()
    
    # Datos históricos (últimos 90 días)
    recent_data = daily_counts.tail(90)
    fig.add_trace(go.Scatter(
        x=recent_data['FechaExpendiente'],
        y=recent_data['Ingresos'],
        mode='lines+markers',
        name='Datos Históricos',
        line=dict(color='#2ecc71')
    ))
    
    # Predicciones
    fig.add_trace(go.Scatter(
        x=future_dates,
        y=predictions,
        mode='lines+markers',
        name='Predicción',
        line=dict(color='#e74c3c', dash='dash')
    ))
    
    fig.update_layout(
        title="Tendencia y Predicción de Ingresos (90 días históricos + 30 días futuros)",
        xaxis_title="Fecha",
        yaxis_title="Expedientes",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_key_metrics(data):
    """Muestra métricas clave y predicciones"""
    daily_counts = data.groupby(data['FechaExpendiente'].dt.date).size()
    
    # Métricas clave
    st.subheader("📈 Métricas Clave")
    
    # Promedio histórico
    promedio = daily_counts.mean()
    st.metric(
        "Promedio Diario",
        f"{promedio:.0f}",
        help="Promedio histórico de ingresos por día"
    )
    
    # Máximo histórico
    maximo = daily_counts.max()
    fecha_max = daily_counts.idxmax()
    st.metric(
        "Máximo Histórico",
        f"{maximo:.0f}",
        f"({fecha_max.strftime('%d/%m/%Y')})",
        help="Mayor número de ingresos en un día"
    )
    
    # Carga actual vs promedio
    ultimo_dia = daily_counts.index.max()
    carga_actual = daily_counts.get(ultimo_dia, 0)
    variacion = ((carga_actual - promedio) / promedio) * 100
    st.metric(
        "Carga Actual",
        f"{carga_actual:.0f}",
        f"{variacion:+.1f}% vs promedio",
        help="Ingresos del último día vs promedio histórico"
    )

def render_temporal_insights(data):
    """Análisis temporal detallado"""
    st.subheader("📅 Análisis Temporal")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Análisis por día de la semana
        data['DiaSemana'] = data['FechaExpendiente'].dt.day_name()
        dias_orden = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dias_esp = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        dia_mapping = dict(zip(dias_orden, dias_esp))
        
        ingresos_por_dia = data.groupby(data['DiaSemana']).size()
        ingresos_por_dia.index = ingresos_por_dia.index.map(dia_mapping)
        
        fig_dias = px.bar(
            ingresos_por_dia,
            title="Distribución de Ingresos por Día",
            labels={'value': 'Cantidad', 'index': 'Día'},
            color_discrete_sequence=['#3498db']
        )
        st.plotly_chart(fig_dias, use_container_width=True)
    
    with col2:
        # Análisis por hora del día
        data['Hora'] = data['FechaExpendiente'].dt.hour
        ingresos_por_hora = data.groupby('Hora').size()
        
        fig_horas = px.line(
            ingresos_por_hora,
            title="Patrón de Ingresos por Hora",
            labels={'value': 'Cantidad', 'index': 'Hora'},
            line_shape='spline'
        )
        st.plotly_chart(fig_horas, use_container_width=True)

def render_patterns_analysis(data):
    """Análisis de patrones y anomalías"""
    st.subheader("🔍 Patrones y Anomalías")
    
    # Detectar días atípicos
    daily_counts = data.groupby(data['FechaExpendiente'].dt.date).size()
    mean = daily_counts.mean()
    std = daily_counts.std()
    
    anomalias = daily_counts[abs(daily_counts - mean) > 2 * std]
    
    if not anomalias.empty:
        st.warning("📊 Días con Ingresos Atípicos")
        anomalias_df = pd.DataFrame({
            'Fecha': anomalias.index,
            'Ingresos': anomalias.values,
            'Desviación': ((anomalias - mean) / std).round(2)
        })
        anomalias_df['Fecha'] = anomalias_df['Fecha'].dt.strftime('%d/%m/%Y')
        st.dataframe(
            anomalias_df.sort_values('Desviación', ascending=False),
            hide_index=True
        )
    
    # Análisis de estacionalidad
    st.info("📈 Insights de Estacionalidad")
    col1, col2 = st.columns(2)
    
    with col1:
        # Variación mensual
        monthly_avg = data.groupby(data['FechaExpendiente'].dt.month).size().mean()
        current_month = datetime.now().month
        current_month_count = len(data[data['FechaExpendiente'].dt.month == current_month])
        
        st.metric(
            "Promedio Mensual",
            f"{monthly_avg:.0f}",
            f"{((current_month_count - monthly_avg) / monthly_avg * 100):+.1f}% este mes"
        )
    
    with col2:
        # Identificar mejor y peor día
        ingresos_por_dia = data.groupby(data['FechaExpendiente'].dt.day_name()).size()
        mejor_dia = ingresos_por_dia.idxmax()
        peor_dia = ingresos_por_dia.idxmin()
        
        st.write(f"🔝 Mejor día: **{dia_mapping[mejor_dia]}**")
        st.write(f"⬇️ Día más bajo: **{dia_mapping[peor_dia]}**") 