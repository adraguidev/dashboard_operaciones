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
        st.header("📊 Análisis de Ingreso de Expedientes")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que las fechas son válidas
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')
        data = data.dropna(subset=['FechaExpendiente'])

        # 1. Tendencias y Predicciones
        st.subheader("📈 Tendencias y Predicciones de Ingresos")
        render_trends_and_predictions(data)
        
        st.markdown("---")
        
        # 2. Análisis Temporal
        st.subheader("📅 Análisis Temporal de Ingresos")
        render_temporal_analysis(data)
        
        st.markdown("---")
        
        # 3. Estadísticas Generales
        st.subheader("📊 Estadísticas Generales")
        render_general_statistics(data)

    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        print(f"Error detallado: {str(e)}")

def render_trends_and_predictions(data):
    """Renderiza gráficos de tendencias y predicciones"""
    daily_counts = data.groupby(data['FechaExpendiente'].dt.date).size().reset_index(name='Ingresos')
    daily_counts['FechaExpendiente'] = pd.to_datetime(daily_counts['FechaExpendiente'])
    
    # Crear modelo de predicción polinomial
    X = np.arange(len(daily_counts)).reshape(-1, 1)
    poly = PolynomialFeatures(degree=2)
    X_poly = poly.fit_transform(X)
    
    model = LinearRegression()
    model.fit(X_poly, daily_counts['Ingresos'])
    
    # Generar predicciones para los próximos 30 días
    future_dates = pd.date_range(
        start=daily_counts['FechaExpendiente'].max(), 
        periods=31, 
        freq='D'
    )[1:]
    
    X_future = np.arange(len(daily_counts), len(daily_counts) + 30).reshape(-1, 1)
    X_future_poly = poly.transform(X_future)
    predictions = model.predict(X_future_poly)
    
    # Crear gráfico interactivo
    fig = go.Figure()
    
    # Datos históricos (últimos 90 días)
    recent_data = daily_counts.tail(90)
    fig.add_trace(go.Scatter(
        x=recent_data['FechaExpendiente'],
        y=recent_data['Ingresos'],
        mode='lines+markers',
        name='Datos Históricos',
        line=dict(color='blue')
    ))
    
    # Predicciones
    fig.add_trace(go.Scatter(
        x=future_dates,
        y=predictions,
        mode='lines+markers',
        name='Predicción',
        line=dict(color='red', dash='dash')
    ))
    
    fig.update_layout(
        title="Ingresos Diarios y Predicción (Últimos 90 días + 30 días futuros)",
        xaxis_title="Fecha",
        yaxis_title="Número de Expedientes",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Mostrar métricas de predicción
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Promedio Histórico",
            f"{daily_counts['Ingresos'].mean():.0f}",
            help="Promedio histórico de ingresos diarios"
        )
    with col2:
        st.metric(
            "Predicción Promedio",
            f"{predictions.mean():.0f}",
            help="Promedio de ingresos diarios predichos"
        )
    with col3:
        tendencia = "🔼" if predictions[-1] > predictions[0] else "🔽"
        st.metric(
            "Tendencia",
            tendencia,
            help="Tendencia de la predicción para los próximos 30 días"
        )

def render_temporal_analysis(data):
    """Renderiza análisis temporal (mensual y anual)"""
    col1, col2 = st.columns(2)
    
    with col1:
        # Análisis mensual del año actual
        current_year = datetime.now().year
        monthly_data = data[data['FechaExpendiente'].dt.year == current_year].groupby(
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
            title=f"Ingresos Mensuales {current_year}",
            labels={'value': 'Cantidad de Expedientes', 'index': 'Mes'},
            color_discrete_sequence=['#2ecc71']
        )
        st.plotly_chart(fig_monthly, use_container_width=True)
    
    with col2:
        # Análisis anual
        yearly_data = data.groupby(data['FechaExpendiente'].dt.year).size()
        fig_yearly = px.bar(
            yearly_data,
            title="Ingresos Anuales",
            labels={'value': 'Cantidad de Expedientes', 'index': 'Año'},
            color_discrete_sequence=['#3498db']
        )
        st.plotly_chart(fig_yearly, use_container_width=True)

def render_general_statistics(data):
    """Renderiza estadísticas generales"""
    # Calcular estadísticas
    total_expedientes = len(data)
    promedio_diario = data.groupby(data['FechaExpendiente'].dt.date).size().mean()
    max_diario = data.groupby(data['FechaExpendiente'].dt.date).size().max()
    fecha_max = data.groupby(data['FechaExpendiente'].dt.date).size().idxmax()
    
    # Mostrar métricas en cards
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Total de Expedientes",
            f"{total_expedientes:,d}",
            help="Número total de expedientes ingresados"
        )
        st.metric(
            "Promedio Diario",
            f"{promedio_diario:.1f}",
            help="Promedio de expedientes ingresados por día"
        )
    
    with col2:
        st.metric(
            "Máximo Diario",
            f"{max_diario:,d}",
            help="Máximo número de expedientes ingresados en un día"
        )
        st.metric(
            "Fecha de Máximo Ingreso",
            fecha_max.strftime("%d/%m/%Y"),
            help="Fecha en que se registró el máximo ingreso"
        )