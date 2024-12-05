import streamlit as st
import pandas as pd
import plotly.express as px
from sklearn.linear_model import LinearRegression
import numpy as np
import plotly.graph_objects as go

def render_entry_analysis_tab(data):
    st.header("Ingreso de Expedientes")
    st.info("Gráficos de tendencias y predicciones sobre ingresos de expedientes.")

    # Gráfico principal de ingresos diarios
    render_daily_entries_chart(data)
    
    # Tabla de ingresos diarios
    render_daily_entries_table(data)

def render_daily_entries_chart(data):
    st.subheader("Evolución de Ingresos Diarios (Últimos 45 días)")
    
    # Preparar datos
    last_45_days_data = data[data['FechaExpendiente'] >= (pd.Timestamp.now() - pd.DateOffset(days=45))]
    daily_counts = last_45_days_data.groupby(last_45_days_data['FechaExpendiente'].dt.date).size().reset_index(name='Ingresos')
    daily_counts['FechaExpendiente'] = pd.to_datetime(daily_counts['FechaExpendiente'])
    
    # Crear línea de tendencia y predicción
    X = np.arange(len(daily_counts)).reshape(-1, 1)
    y = daily_counts['Ingresos'].values
    model = LinearRegression()
    model.fit(X, y)
    
    trend = model.predict(X)
    future_days = np.arange(len(daily_counts), len(daily_counts) + 7).reshape(-1, 1)
    future_predictions = model.predict(future_days)
    future_dates = pd.date_range(start=daily_counts['FechaExpendiente'].iloc[-1], periods=8, freq='D')[1:]
    
    # Crear gráfico
    fig = go.Figure()
    
    # Datos históricos
    fig.add_trace(go.Scatter(
        x=daily_counts['FechaExpendiente'],
        y=daily_counts['Ingresos'],
        mode='lines+markers',
        name='Ingresos Diarios',
        line=dict(color='blue')
    ))
    
    # Línea de tendencia
    fig.add_trace(go.Scatter(
        x=daily_counts['FechaExpendiente'],
        y=trend,
        mode='lines',
        name='Tendencia',
        line=dict(color='red', dash='dot')
    ))
    
    # Predicciones
    fig.add_trace(go.Scatter(
        x=future_dates,
        y=future_predictions,
        mode='lines+markers',
        name='Predicción',
        line=dict(color='green', dash='dash')
    ))
    
    fig.update_layout(
        title="Ingresos Diarios y Predicción",
        xaxis_title="Fecha",
        yaxis_title="Número de Expedientes",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig)
    
    # Mostrar estadísticas
    avg_prediction = future_predictions.mean()
    st.write(f"""
    **Análisis de Tendencia:**
    - Promedio de ingresos predichos: {avg_prediction:.1f} expedientes/día
    - Tendencia: {'Creciente' if model.coef_[0] > 0 else 'Decreciente'}
    """)

def render_daily_entries_table(data):
    st.subheader("Detalle de Ingresos Diarios (Últimos 30 días)")
    
    # Preparar datos
    last_30_days = data[data['FechaExpendiente'] >= (pd.Timestamp.now() - pd.DateOffset(days=30))]
    daily_counts = last_30_days.groupby(last_30_days['FechaExpendiente'].dt.date).agg({
        'NumeroTramite': 'count',
        'TipoTramite': lambda x: ', '.join(x.unique())
    }).reset_index()
    
    daily_counts.columns = ['Fecha', 'Total Ingresos', 'Tipos de Trámite']
    daily_counts['Fecha'] = daily_counts['Fecha'].dt.strftime('%d/%m/%Y')
    
    # Mostrar tabla
    st.dataframe(
        daily_counts.sort_values('Fecha', ascending=False),
        use_container_width=True
    ) 