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
from io import BytesIO

st.set_page_config(layout="wide")

# Módulos habilitados
modules = {
    'CCM': '📊 CCM',
    'PRR': '📈 PRR',
    'CCM-ESP': '📉 CCM-ESP',
    'CCM-LEY': '📋 CCM-LEY', 
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
        # Mostrar estadísticas iniciales
        
        # Filtrar CCM-LEY: registros de CCM que no están en CCM-ESP
        ccm_ley_data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]

        # Verificar estadísticas después de la exclusión
        
        # Validar columnas necesarias
        required_columns = ['FechaExpendiente', 'FechaPre']
        for col in required_columns:
            if col not in ccm_ley_data.columns:
                st.error(f"Falta la columna requerida: {col}")
                return None

        # Asegurarnos de que las fechas se interpreten correctamente
        try:
            ccm_ley_data['FechaExpendiente'] = pd.to_datetime(ccm_ley_data['FechaExpendiente'], format='%d/%m/%Y', errors='coerce')
            ccm_ley_data['FechaPre'] = pd.to_datetime(ccm_ley_data['FechaPre'], format='%d/%m/%Y', errors='coerce')
        except Exception as e:
            st.error(f"Error al convertir las fechas: {e}")
            return None

        # Identificar registros con fechas inconsistentes
        invalid_dates = ccm_ley_data[ccm_ley_data['FechaExpendiente'] > ccm_ley_data['FechaPre']]

        # Descargar registros con fechas inconsistentes
        if not invalid_dates.empty:
            st.subheader("Descarga de registros con fechas inconsistentes")
            # Crear un buffer de memoria para almacenar el Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                invalid_dates.to_excel(writer, index=False, sheet_name='Fechas Inconsistentes')
            output.seek(0)  # Volver al inicio del buffer

            # Botón de descarga
            st.download_button(
                label="Descargar registros inconsistentes",
                data=output,
                file_name="registros_inconsistentes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
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
    tabs = st.tabs(["Dashboard de Pendientes", "Ingreso de Expedientes", "Cierre de Expedientes","Reporte por Evaluador"])
    
# Listas de evaluadores inactivos por módulo
inactive_evaluators = {
    "CCM": [
        "Mauricio Romero, Hugo",
        "Ugarte Sánchez, Paulo César",
        "Santibañez Chafalote, Lila Mariella",
        "Quispe Orosco, Karina Wendy",
        "Miranda Avila, Marco Antonio",
        "Aponte Sanchez, Paola Lita",
        "Orcada Herrera, Javier Eduardo",
        "Gomez Vera, Marcos Alberto",
        "VULNERABILIDAD",
        "SUSPENDIDA"
    ],
    "PRR": [
        "Pozo Ferro, Sonia Leonor",
        "Bautista Lopez, Diana Carolina",
        "Infantes Panduro, Jheyson",
        "Vizcardo Ordoñez, Fiorella Carola",
        "Ponce Malpartida, Miguel",
        "Valdez Gallo, Cynthia Andrea",
        "Hurtado Lago Briyan Deivi",
        "Diaz Amaya, Esthefany Lisset",
        "Santibañez Chafalote, Lila Mariella",
        "Pumallanque Ramirez, Mariela",
        "Valera Gaviria, Jessica Valeria",
        "Vásquez Fernandez, Anthony Piere",
        "VULNERABILIDAD",
        "SUSPENDIDA"
    ]
}

# Pestaña 1: Dashboard de Pendientes
with tabs[0]:
    st.header("Dashboard de Pendientes")

    # Determinar evaluadores inactivos según el módulo seleccionado
    if selected_module in ['CCM', 'CCM-ESP', 'CCM-LEY']:
        module_inactive_evaluators = inactive_evaluators.get('CCM', [])
    elif selected_module == 'PRR':
        module_inactive_evaluators = inactive_evaluators.get('PRR', [])
    else:
        module_inactive_evaluators = []

    # Selección de vista (Activos, Inactivos, Total)
    st.subheader("Selecciona la Vista")
    view_option = st.radio(
        "Elige qué evaluadores deseas visualizar:",
        options=["Activos", "Inactivos", "Total"],
        index=0
    )

    # Selección de años
    selected_years = st.multiselect("Selecciona los Años", sorted(data['Anio'].unique()))

    # Obtener todos los evaluadores del módulo actual
    all_evaluators = sorted(data['EVALASIGN'].dropna().unique())

    # Filtrar evaluadores según la opción seleccionada
    if view_option == "Activos":
        evaluators = [e for e in all_evaluators if e not in module_inactive_evaluators]
    elif view_option == "Inactivos":
        evaluators = [e for e in all_evaluators if e in module_inactive_evaluators]
    else:  # Total
        evaluators = all_evaluators

    # Mostrar filtro de evaluadores
    st.subheader(f"Evaluadores ({view_option})")
    selected_evaluators = []
    with st.expander(f"Filtro de Evaluadores ({view_option})", expanded=False):
        select_all = st.checkbox("Seleccionar Todos", value=True)  # No seleccionados por defecto
        if select_all:
            selected_evaluators = evaluators
        else:
            for evaluator in evaluators:
                if st.checkbox(evaluator, value=False, key=f"{selected_module}_checkbox_{evaluator}"):
                    selected_evaluators.append(evaluator)

    # Mostrar tabla y descargas si se seleccionan años
    if selected_years:
        # Filtrar solo los pendientes (Evaluado == NO)
        filtered_data = data[data['Evaluado'] == 'NO']

        # Filtrar según los evaluadores seleccionados
        if selected_evaluators:
            filtered_data = filtered_data[filtered_data['EVALASIGN'].isin(selected_evaluators)]

        if len(selected_years) > 1:
            # Generar tabla para múltiples años
            table = generate_table_multiple_years(filtered_data, selected_years, selected_evaluators)
            total_pendientes = table['Total'].sum()
            st.metric("Total de Expedientes Pendientes", total_pendientes)
            render_table(table, f"Pendientes por Evaluador ({view_option}, Varios Años)")

            # Descarga como Excel
            excel_buf = download_table_as_excel(table, f"Pendientes_{view_option}_Varios_Años")
            st.download_button(
                "Descargar como Excel",
                excel_buf,
                file_name=f"pendientes_{view_option.lower()}_varios_anos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            # Generar tabla para un solo año
            table = generate_table_single_year(filtered_data, selected_years[0], selected_evaluators)
            total_pendientes = table['Total'].sum()
            st.metric("Total de Expedientes Pendientes", total_pendientes)
            render_table(table, f"Pendientes por Evaluador ({view_option}, Año {selected_years[0]})")

            # Descarga como Excel
            excel_buf = download_table_as_excel(table, f"Pendientes_{view_option}_Año_{selected_years[0]}")
            st.download_button(
                "Descargar como Excel",
                excel_buf,
                file_name=f"pendientes_{view_option.lower()}_año_{selected_years[0]}.xlsx",
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
            file_name=f"pendientes_detallado_{view_option.lower()}.xlsx",
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

    # Tabla de ingresos diarios detallados en formato pivot
    st.subheader("Ingresos Diarios Detallados (Últimos 30 Días)")
    last_30_days_data = data[data['FechaExpendiente'] >= (pd.Timestamp.now() - pd.DateOffset(days=30))]
    daily_counts_30 = last_30_days_data.groupby(last_30_days_data['FechaExpendiente'].dt.date).size().reset_index(name='Ingresos')
    daily_counts_30['FechaExpendiente'] = pd.to_datetime(daily_counts_30['FechaExpendiente']).dt.strftime('%d/%m')
    pivot_table_30 = daily_counts_30.set_index('FechaExpendiente').transpose()

    st.table(pivot_table_30)

    # Gráfico 2: Pronóstico de ingresos diarios con Prophet

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

    # Asegurarnos de que 'FechaExpendiente' y 'FechaPre' estén en formato datetime
    data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')
    data['FechaPre'] = pd.to_datetime(data['FechaPre'], errors='coerce')

    # Selección del rango de fechas para la Matriz de Cierre
    st.subheader("Selecciona el Rango de Fechas para la Matriz de Cierre")
    range_options = ["Últimos 15 días", "Últimos 30 días", "Durante el último mes"]
    selected_range = st.radio("Rango de Fechas", range_options, index=0)

    # Determinar el rango de fechas basado en la selección
    if selected_range == "Últimos 15 días":
        date_threshold = pd.Timestamp.now() - pd.DateOffset(days=15)
    elif selected_range == "Últimos 30 días":
        date_threshold = pd.Timestamp.now() - pd.DateOffset(days=30)
    elif selected_range == "Durante el último mes":
        date_threshold = pd.Timestamp.now().replace(day=1)  # Inicio del mes actual

    cierre_data_range = data[data['FechaPre'] >= date_threshold].copy()

    # Agrupar por evaluador y fecha de cierre
    cierre_matrix = cierre_data_range.groupby(['EVALASIGN', cierre_data_range['FechaPre'].dt.date]).size().unstack(fill_value=0)

    # Limitar las columnas de la matriz a las fechas seleccionadas
    cierre_matrix = cierre_matrix.loc[:, cierre_matrix.columns]

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
    st.subheader(f"Matriz de Cierre de Expedientes ({selected_range})")
    st.dataframe(cierre_matrix)

    # Filtro de período dinámico para otros análisis
    st.subheader("Selecciona el Período de Análisis")
    period_options = ["Últimos 30 días", "Últimos 3 meses", "Últimos 6 meses"]
    selected_period = st.radio("Período", period_options, index=1)  # Por defecto, selecciona "Últimos 3 meses"

    # Filtrar datos según el período seleccionado
    if selected_period == "Últimos 30 días":
        start_date = pd.Timestamp.now() - pd.DateOffset(days=30)
    elif selected_period == "Últimos 3 meses":
        start_date = pd.Timestamp.now() - pd.DateOffset(months=3)
    elif selected_period == "Últimos 6 meses":
        start_date = pd.Timestamp.now() - pd.DateOffset(months=6)

    cierre_data = data[data['FechaExpendiente'] >= start_date].copy()

    # Validar fechas: excluir registros con inconsistencias
    valid_cierre_data = cierre_data[cierre_data['FechaPre'] >= cierre_data['FechaExpendiente']]
    invalid_cierre_data = cierre_data[cierre_data['FechaPre'] < cierre_data['FechaExpendiente']]

    # Mostrar advertencia sobre registros excluidos
    if len(invalid_cierre_data) > 0:
        st.warning(f"Se excluyeron {len(invalid_cierre_data)} registros con fechas inconsistentes.")
        
        # Botón para descargar los registros inconsistentes
        st.subheader("Descargar registros con fechas inconsistentes")
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            invalid_cierre_data.to_excel(writer, index=False, sheet_name='Fechas Inconsistentes')
        output.seek(0)  # Volver al inicio del buffer

        st.download_button(
            label="Descargar registros inconsistentes",
            data=output,
            file_name="fechas_inconsistentes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Reemplazar el cierre_data con los datos válidos
    cierre_data = valid_cierre_data

    # Calcular el tiempo promedio de cierre por evaluador
    cierre_data['TiempoCierre'] = (cierre_data['FechaPre'] - cierre_data['FechaExpendiente']).dt.days
    tiempo_promedio_general = cierre_data['TiempoCierre'].mean()

    # Agrupar por evaluador para calcular el promedio de tiempo de cierre
    tiempo_promedio_por_evaluador = cierre_data.groupby('EVALASIGN')['TiempoCierre'].mean().reset_index()
    tiempo_promedio_por_evaluador.rename(columns={'TiempoCierre': 'PromedioDíasCierre'}, inplace=True)
    tiempo_promedio_por_evaluador = tiempo_promedio_por_evaluador.sort_values(by='PromedioDíasCierre', ascending=False)

    # Mostrar el tiempo promedio general
    st.metric(f"Tiempo Promedio General de Cierre ({selected_period})", f"{tiempo_promedio_general:.2f} días")

    # Mostrar tabla de tiempos promedio por evaluador
    st.subheader(f"Tiempos Promedio de Cierre por Evaluador ({selected_period})")
    st.dataframe(tiempo_promedio_por_evaluador[['EVALASIGN', 'PromedioDíasCierre']].reset_index(drop=True))  # Eliminar índice

    # Distribución de cierres por tiempo en días con 10 categorías fijas
    bins = [1, 3, 6, 9, 12, 15, 18, 21, 24, 28, float('inf')]  # Categorías fijas
    labels = [
        "1-3 días", "4-6 días", "7-9 días", "10-12 días",
        "13-15 días", "16-18 días", "19-21 días", "22-24 días",
        "25-28 días", "28+ días"
    ]
    cierre_data['CategoríaTiempo'] = pd.cut(
        cierre_data['TiempoCierre'],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    cierre_categorías = cierre_data['CategoríaTiempo'].value_counts(normalize=True).sort_index() * 100

    st.subheader(f"Distribución de Cierres por Tiempo ({selected_period})")
    fig_categorías = px.bar(
        cierre_categorías,
        x=cierre_categorías.index,
        y=cierre_categorías.values,
        title=f"Cierres de Expedientes por Tiempo ({selected_period})",
        labels={'x': "Categoría de Tiempo", 'y': "Porcentaje de Expedientes"},
        text_auto=True
    )
    st.plotly_chart(fig_categorías)

    st.write("""
    **Interpretación del Indicador:**
    - El gráfico muestra la distribución porcentual de los expedientes según el tiempo tomado para su cierre.
    - Las categorías ayudan a identificar patrones de eficiencia en los cierres.
    """)


# Pestaña 4: Reporte por Evaluador
with tabs[3]:
    st.header("Reporte por Evaluador")
    st.info("Genera un reporte personalizado de expedientes pendientes por evaluador, año y mes.")

    # Obtener lista de evaluadores con pendientes (Evaluado == 'NO') en el módulo actual
    evaluators_with_pendings = sorted(data[data['Evaluado'] == 'NO']['EVALASIGN'].dropna().unique())

    # Desplegable para seleccionar el evaluador (solo con evaluadores que tienen pendientes)
    selected_evaluator = st.selectbox("Selecciona un Evaluador", options=evaluators_with_pendings)

    # Multiselección para seleccionar años disponibles
    available_years = sorted(data['Anio'].unique())
    selected_years = st.multiselect("Selecciona el Año o Años", options=available_years)

    # Mostrar opción para seleccionar uno o varios meses si se elige al menos un año
    selected_months = None
    if selected_years:
        # Obtener los meses disponibles para los años seleccionados
        months = sorted(data[data['Anio'].isin(selected_years)]['Mes'].unique())
        month_names = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        month_options = [month_names[m] for m in months]
        month_mapping = {v: k for k, v in month_names.items()}
        selected_month_names = st.multiselect("Selecciona uno o varios Meses", options=month_options)
        selected_months = [month_mapping[m] for m in selected_month_names]  # Convertir nombres a números

    # Filtrar datos según el evaluador, años y meses seleccionados
    filtered_data = data[data['EVALASIGN'] == selected_evaluator]

    if selected_years:
        filtered_data = filtered_data[filtered_data['Anio'].isin(selected_years)]

    if selected_months:
        filtered_data = filtered_data[filtered_data['Mes'].isin(selected_months)]

    # Filtrar pendientes (Evaluado == 'NO')
    filtered_data = filtered_data[filtered_data['Evaluado'] == 'NO']

    # Mostrar tabla con los expedientes pendientes
    if not filtered_data.empty:
        st.subheader(f"Reporte de Expedientes Pendientes ({selected_evaluator})")
        st.dataframe(filtered_data)

        # Botón para descargar los datos como Excel
        st.subheader("Descarga de Reporte")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            filtered_data.to_excel(writer, index=False, sheet_name='Reporte')
        output.seek(0)

        st.download_button(
            label="Descargar Reporte en Excel",
            data=output,
            file_name=f"Reporte_{selected_evaluator}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No se encontraron expedientes pendientes para los filtros seleccionados.")
