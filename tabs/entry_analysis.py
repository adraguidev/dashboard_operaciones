import streamlit as st
import pandas as pd
import plotly.express as px
from prophet import Prophet
from sklearn.linear_model import LinearRegression
import numpy as np

def render_entry_analysis_tab(data):
    st.header("Ingreso de Expedientes")
    st.info("Gráficos de tendencias y predicciones sobre ingresos de expedientes.")

    # Gráfico 1: Ingresos diarios durante los últimos 45 días
    render_daily_entries_chart(data)
    
    # Tabla de ingresos diarios detallados
    render_daily_entries_table(data)
    
    # Pronóstico con Prophet
    render_prophet_forecast(data)

def render_daily_entries_chart(data):
    st.subheader("Evolución de Ingresos Diarios (Últimos 45 días)")
    
    # Preparar datos
    fecha_actual = pd.Timestamp.now().date()
    last_45_days_data = data[data['FechaExpendiente'] >= (pd.Timestamp.now() - pd.DateOffset(days=45))]
    daily_counts_45 = last_45_days_data.groupby(last_45_days_data['FechaExpendiente'].dt.date).size().reset_index(name='Ingresos')
    daily_counts_45['FechaExpendiente'] = pd.to_datetime(daily_counts_45['FechaExpendiente'])
    
    # Crear línea de tendencia
    X_days_45 = np.arange(len(daily_counts_45)).reshape(-1, 1)
    y_days_45 = daily_counts_45['Ingresos']
    model_days_45 = LinearRegression()
    model_days_45.fit(X_days_45, y_days_45)
    trend_days_45 = model_days_45.predict(X_days_45)
    
    # Predicción próximos 7 días
    future_days_45 = np.arange(len(daily_counts_45) + 7).reshape(-1, 1)
    future_predictions_45 = model_days_45.predict(future_days_45)
    future_dates_45 = pd.date_range(start=daily_counts_45['FechaExpendiente'].iloc[-1], periods=8, freq='D')[1:]
    
    # Graficar
    fig_daily_45 = px.line(daily_counts_45, x='FechaExpendiente', y='Ingresos', 
                          title="Ingresos Diarios (Últimos 45 Días)", markers=True)
    fig_daily_45.add_scatter(x=daily_counts_45['FechaExpendiente'], y=trend_days_45, 
                            mode='lines', line=dict(color='red', dash='dot'), name='Tendencia')
    fig_daily_45.add_scatter(x=future_dates_45, y=future_predictions_45[-7:], 
                            mode='lines+markers', line=dict(color='green', dash='dash'), 
                            name='Predicción (Próximos 7 días)')
    st.plotly_chart(fig_daily_45)
    
    st.write("""
    **Interpretación del Gráfico:**
    - Este gráfico muestra los ingresos diarios de expedientes en los últimos 45 días.
    - La línea roja punteada indica la tendencia general de los ingresos diarios.
    - La línea verde discontinua proyecta los ingresos diarios para los próximos 7 días.
    """)

def render_daily_entries_table(data):
    st.subheader("Ingresos Diarios Detallados (Últimos 30 Días)")
    
    last_30_days_data = data[data['FechaExpendiente'] >= (pd.Timestamp.now() - pd.DateOffset(days=30))]
    daily_counts_30 = last_30_days_data.groupby(last_30_days_data['FechaExpendiente'].dt.date).size().reset_index(name='Ingresos')
    daily_counts_30['FechaExpendiente'] = pd.to_datetime(daily_counts_30['FechaExpendiente']).dt.strftime('%d/%m')
    pivot_table_30 = daily_counts_30.set_index('FechaExpendiente').transpose()
    
    st.table(pivot_table_30)

def render_prophet_forecast(data):
    st.subheader("Pronóstico de Ingresos Diarios (Optimizado para los Próximos 30 Días)")
    
    # Preparar datos para Prophet
    historical_data = data[['FechaExpendiente']].copy()
    historical_data['ds'] = historical_data['FechaExpendiente']
    daily_counts = historical_data.groupby(historical_data['ds'].dt.date).size().reset_index(name='y')
    daily_counts['ds'] = pd.to_datetime(daily_counts['ds'])
    daily_counts = daily_counts[['ds', 'y']]

    # Crear y entrenar modelo Prophet
    model = Prophet(daily_seasonality=True, yearly_seasonality=True)
    model.fit(daily_counts)

    # Generar pronóstico
    future_dates = model.make_future_dataframe(periods=30)
    forecast = model.predict(future_dates)
    
    # Filtrar para visualización
    forecast_focus = forecast[(forecast['ds'] >= (pd.Timestamp.now() - pd.DateOffset(days=60)))]
    
    # Crear gráfico
    fig_prophet = px.line(forecast_focus, x='ds', y='yhat', 
                         title="Pronóstico de Ingresos Diarios (30 días)",
                         labels={'ds': 'Fecha', 'yhat': 'Ingresos Estimados'})
    
    fig_prophet.add_scatter(x=forecast_focus['ds'], y=forecast_focus['yhat'],
                          mode='lines', line=dict(color='green', width=3),
                          name='Pronóstico')
    
    fig_prophet.add_scatter(x=forecast_focus['ds'], y=forecast_focus['yhat_lower'],
                          mode='lines', line=dict(color='blue', dash='dot', width=1),
                          name='Límite Inferior')
    
    fig_prophet.add_scatter(x=forecast_focus['ds'], y=forecast_focus['yhat_upper'],
                          mode='lines', line=dict(color='blue', dash='dot', width=1),
                          name='Límite Superior')
    
    st.plotly_chart(fig_prophet)
    
    # Mostrar resumen estadístico
    avg_prediction = forecast['yhat'][-30:].mean()
    st.write(f"""
    En promedio, se estima que el ingreso diario de expedientes para los próximos 30 días 
    será de aproximadamente **{avg_prediction:.2f} expedientes por día**.
    """) 