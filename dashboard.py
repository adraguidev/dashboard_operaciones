import os
import pandas as pd
import streamlit as st
import plotly.express as px
from dashboard_table_generator import generate_table_multiple_years, generate_table_single_year
from dashboard_downloads import download_table_as_excel, download_detailed_list
from dashboard_utils import render_table
from sklearn.linear_model import LinearRegression
import numpy as np
from prophet import Prophet
import plotly.graph_objects as go

# Módulos habilitados
modules = {
    'CCM': '📊 CCM',
    'PRR': '📈 PRR',
    'CCM-ESP': '📉 CCM-ESP',
    'CCM-LEY': '📋 CCM-LEY',  # Añadido CCM-LEY
    'SOL': '📂 SOL',
}

st.title("Gestión de Expedientes")

@st.cache_data
def load_consolidated_cached(module_name):
    folder = f"descargas/{module_name}"
    for file in os.listdir(folder):
        if file.startswith(f"Consolidado_{module_name}_CRUZADO") and file.endswith(".xlsx"):
            file_path = os.path.join(folder, file)
            data = pd.read_excel(file_path)
            data['Anio'] = data['Anio'].astype(int)
            data['Mes'] = data['Mes'].astype(int)
            data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'])  # Aseguramos formato de fecha
            return data
    return None

# Lógica para CCM-LEY usando CCM y excluyendo CCM-ESP
def load_ccm_ley_data():
    # Cargar datos de CCM y CCM-ESP
    ccm_data = load_consolidated_cached('CCM')
    ccm_esp_data = load_consolidated_cached('CCM-ESP')
    
    if ccm_data is not None and ccm_esp_data is not None:
        # Filtrar CCM-LEY: registros de CCM que no están en CCM-ESP
        ccm_ley_data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
        
        return ccm_ley_data
    
    st.error("No se pudo cargar la información de CCM o CCM-ESP.")
    return None


# Menú de navegación para módulos
selected_module = st.sidebar.radio(
    "Selecciona un módulo",
    options=list(modules.keys()),
    format_func=lambda x: modules[x]
)

# Cargar datos del módulo
if selected_module == 'CCM-LEY':
    data = load_ccm_ley_data()
else:
    data = load_consolidated_cached(selected_module)

if data is None:
    st.error("No se encontró el archivo consolidado para este módulo.")
else:
    # Crear pestañas para el módulo
    tabs = st.tabs(["Dashboard de Pendientes", "Ingreso de Expedientes", "Cierre de Expedientes"])
    
    # Pestaña 1: Dashboard de Pendientes
    with tabs[0]:
        st.header("Dashboard de Pendientes")
        
        # Selección de años
        selected_years = st.multiselect("Selecciona los Años", sorted(data['Anio'].unique()))
        
        # Selección de evaluadores con checkboxes compactos
        evaluators = sorted(data['EVALASIGN'].dropna().unique())
        st.subheader("Selecciona los Evaluadores")
        selected_evaluators = []
        with st.expander("Filtro de Evaluadores (Clic para expandir)", expanded=True):
            select_all = st.checkbox("Seleccionar Todos", value=True)
            for evaluator in evaluators:
                if select_all or st.checkbox(evaluator, value=True, key=f"checkbox_{evaluator}"):
                    selected_evaluators.append(evaluator)

        # Mostrar tabla y descargas si se seleccionan años
        if selected_years:
            # Filtrar solo los pendientes (Evaluado == NO)
            filtered_data = data[data['Evaluado'] == 'NO']

            if len(selected_years) > 1:
                # Generar tabla para múltiples años
                table = generate_table_multiple_years(filtered_data, selected_years, selected_evaluators)
                total_pendientes = table['Total'].sum()
                st.metric("Total de Expedientes Pendientes", total_pendientes)
                render_table(table, "Pendientes por Evaluador (Varios Años)")
                
                # Descarga como Excel
                excel_buf = download_table_as_excel(table, "Pendientes Varios Años")
                st.download_button(
                    "Descargar como Excel",
                    excel_buf,
                    file_name="pendientes_varios_anos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                # Generar tabla para un solo año
                table = generate_table_single_year(filtered_data, selected_years[0], selected_evaluators)
                total_pendientes = table['Total'].sum()
                st.metric("Total de Expedientes Pendientes", total_pendientes)
                render_table(table, f"Pendientes por Evaluador ({selected_years[0]})")
                
                # Descarga como Excel
                excel_buf = download_table_as_excel(table, f"Pendientes Año {selected_years[0]}")
                st.download_button(
                    "Descargar como Excel",
                    excel_buf,
                    file_name=f"pendientes_{selected_years[0]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
            # Descarga Detallada
            filters = {
                'Anio': selected_years if selected_years else None,
                'EVALASIGN': selected_evaluators if selected_evaluators else None
            }
            detailed_buf = download_detailed_list(filtered_data, filters)
            st.download_button(
                "Descargar Detallado (Pendientes - Todos los Filtros)",
                detailed_buf,
                file_name="pendientes_detallado_filtrado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Por favor selecciona al menos un año.")

# Pestaña 2: Ingreso de Expedientes
with tabs[1]:
    st.header("Ingreso de Expedientes")
    st.info("Gráficos de tendencias y predicciones sobre ingresos de expedientes.")

    # Gráfico 1: Ingresos diarios durante los últimos 45 días con tendencia y predicción
    st.subheader("Evolución de Ingresos Diarios (Últimos 45 Días)")
    
    # Filtrar los últimos 45 días
    last_45_days_data = data[data['FechaExpendiente'] >= (pd.Timestamp.now() - pd.DateOffset(days=45))]
    daily_counts_45 = last_45_days_data.groupby(last_45_days_data['FechaExpendiente'].dt.date).size().reset_index(name='Ingresos')
    daily_counts_45.rename(columns={'index': 'FechaExpendiente'}, inplace=True)
    daily_counts_45['FechaExpendiente'] = pd.to_datetime(daily_counts_45['FechaExpendiente'])
    
    # Crear línea de tendencia con regresión lineal
    X_days_45 = np.arange(len(daily_counts_45)).reshape(-1, 1)
    y_days_45 = daily_counts_45['Ingresos']
    model_days_45 = LinearRegression()
    model_days_45.fit(X_days_45, y_days_45)
    trend_days_45 = model_days_45.predict(X_days_45)
    
    # Predicción para los próximos 7 días
    future_days_45 = np.arange(len(daily_counts_45) + 7).reshape(-1, 1)
    future_predictions_45 = model_days_45.predict(future_days_45)
    future_dates_45 = pd.date_range(start=daily_counts_45['FechaExpendiente'].iloc[-1], periods=8, freq='D')[1:]
    
    # Combinar datos existentes y predicciones
    pred_df_45 = pd.DataFrame({'FechaExpendiente': future_dates_45, 'Ingresos': future_predictions_45[-7:]})
    combined_df_45 = pd.concat([daily_counts_45, pred_df_45], ignore_index=True)

    # Graficar
    fig_daily_45 = px.line(daily_counts_45, x='FechaExpendiente', y='Ingresos', title="Ingresos Diarios (Últimos 45 Días)", markers=True)
    fig_daily_45.add_scatter(x=daily_counts_45['FechaExpendiente'], y=trend_days_45, mode='lines', line=dict(color='red', dash='dot'), name='Tendencia')
    fig_daily_45.add_scatter(x=future_dates_45, y=future_predictions_45[-7:], mode='lines+markers', line=dict(color='green', dash='dash'), name='Predicción (Próximos 7 días)')
    st.plotly_chart(fig_daily_45)
    
    # Explicación del Gráfico
    st.write("""
    **Interpretación del Gráfico:**
    - Este gráfico muestra los ingresos diarios de expedientes en los últimos 45 días.
    - La línea roja punteada indica la tendencia general de los ingresos diarios.
    - La línea verde discontinua proyecta los ingresos diarios para los próximos 7 días.
    """)

    # Gráfico 2: Pronóstico de ingresos diarios con Prophet
    st.subheader("Pronóstico de Ingresos Diarios")

    # Preparar los datos históricos completos para Prophet
    historical_data = data[['FechaExpendiente']].copy()
    historical_data['ds'] = historical_data['FechaExpendiente']
    daily_counts = historical_data.groupby(historical_data['ds'].dt.date).size().reset_index(name='y')
    daily_counts.rename(columns={'index': 'ds'}, inplace=True)
    daily_counts['ds'] = pd.to_datetime(daily_counts['ds'])  # Aseguramos el formato de fecha
    daily_counts = daily_counts[['ds', 'y']]  # Prophet requiere columnas ds (fecha) y y (valor)

    # Crear modelo Prophet
    model = Prophet(daily_seasonality=True, yearly_seasonality=True)
    model.fit(daily_counts)

    # Generar pronóstico para los próximos 30 días
    future_dates = model.make_future_dataframe(periods=30)
    forecast = model.predict(future_dates)

    # Graficar pronóstico optimizado
    st.subheader("Pronóstico de Ingresos Diarios (Optimizado para los Próximos 30 Días)")

    # Filtrar últimos 60 días históricos + próximos 30 días pronosticados
    forecast_focus = forecast[(forecast['ds'] >= (pd.Timestamp.now() - pd.DateOffset(days=60)))]

    fig_daily_optimized = px.line(
        forecast_focus, 
        x='ds', 
        y='yhat', 
        title="Pronóstico de Ingresos Diarios (30 días)", 
        labels={'ds': 'Fecha', 'yhat': 'Ingresos Estimados'}
    )

    # Resaltar la línea central del pronóstico
    fig_daily_optimized.add_scatter(
        x=forecast_focus['ds'], 
        y=forecast_focus['yhat'], 
        mode='lines', 
        line=dict(color='green', width=3), 
        name='Pronóstico'
    )

    # Límites con menos opacidad
    fig_daily_optimized.add_scatter(
        x=forecast_focus['ds'], 
        y=forecast_focus['yhat_lower'], 
        mode='lines', 
        line=dict(color='blue', dash='dot', width=1), 
        name='Límite Inferior'
    )

    fig_daily_optimized.add_scatter(
        x=forecast_focus['ds'], 
        y=forecast_focus['yhat_upper'], 
        mode='lines', 
        line=dict(color='blue', dash='dot', width=1), 
        name='Límite Superior'
    )

    st.plotly_chart(fig_daily_optimized)

    # Explicación del Pronóstico
    st.write("""
    **Interpretación del Pronóstico:**
    - Este gráfico muestra la tendencia diaria de los ingresos de expedientes basada en datos históricos desde 2018.
    - La línea verde representa el pronóstico central (promedio estimado) para los próximos 30 días.
    - Las líneas azules punteadas indican los límites de confianza superior e inferior, lo que significa que los valores reales podrían variar dentro de este rango.
    - Si la línea de predicción está subiendo, se espera un aumento en los ingresos diarios. Si está bajando, podría haber una disminución.
    """)

    # Resumen Estadístico del Pronóstico
    avg_prediction = forecast['yhat'][-30:].mean()
    st.write(f"""
    En promedio, se estima que el ingreso diario de expedientes para los próximos 30 días será de aproximadamente **{avg_prediction:.2f} expedientes por día**.
    """)

# Pestaña 3: Cierre de Expedientes
with tabs[2]:
    st.header("Cierre de Expedientes")
    st.info("Matriz de cierre de expedientes por evaluador en los últimos 15 días.")

    # Asegurarnos de que 'FechaPre' esté en formato datetime
    data['FechaPre'] = pd.to_datetime(data['FechaPre'], errors='coerce')

    # Filtrar los últimos 15 días
    last_15_days = pd.Timestamp.now() - pd.DateOffset(days=15)
    cierre_data = data[data['FechaPre'] >= last_15_days].copy()

    # Agrupar por evaluador y fecha de cierre
    cierre_matrix = cierre_data.groupby(['EVALASIGN', cierre_data['FechaPre'].dt.date]).size().unstack(fill_value=0)

    # Limitar a los últimos 15 días
    cierre_matrix = cierre_matrix.loc[:, cierre_matrix.columns[-15:]]

    # Renombrar las columnas de fecha a formato dd/mm
    cierre_matrix.columns = [col.strftime('%d/%m') for col in cierre_matrix.columns]

    # Calcular tendencia (aumenta, disminuye, mantiene), ignorando ceros
    tendencias = {}
    for evaluador in cierre_matrix.index:
        series = cierre_matrix.loc[evaluador]
        # Filtrar valores diferentes de cero
        series_nonzero = series[series > 0]
        if series_nonzero.diff().sum() > 0:
            tendencia = "⬆️"
        elif series_nonzero.diff().sum() < 0:
            tendencia = "⬇️"
        else:
            tendencia = "➡️"
        tendencias[evaluador] = tendencia

    # Agregar la tendencia al final de la matriz
    cierre_matrix['Tendencia'] = cierre_matrix.index.map(tendencias)

    # Calcular el promedio de cierre por evaluador
    cierre_matrix['Promedio'] = cierre_matrix.drop(columns=['Tendencia']).mean(axis=1)

    # Ordenar la matriz por promedio de mayor a menor
    cierre_matrix = cierre_matrix.sort_values(by='Promedio', ascending=False)

    # Mostrar la matriz en Streamlit
    st.subheader("Matriz de Cierre de Expedientes (Últimos 15 Días)")
    st.dataframe(cierre_matrix)

    st.write("""
    **Interpretación de la Tendencia:**
    - **⬆️**: El evaluador está cerrando más expedientes en comparación con días anteriores (sin considerar días con cero cierres).
    - **⬇️**: El evaluador está cerrando menos expedientes en comparación con días anteriores.
    - **➡️**: El evaluador está manteniendo un ritmo constante de cierres.
    """)
