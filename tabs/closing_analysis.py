import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import numpy as np

def render_closing_analysis_tab(data: pd.DataFrame):
    try:
        st.header("🎯 Análisis de Cierre de Expedientes")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que las fechas son válidas
        data['FechaPre'] = pd.to_datetime(data['FechaPre'], errors='coerce')
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')
        
        # Filtrar datos nulos
        data = data.dropna(subset=['FechaPre', 'FechaExpendiente'])

        # 1. Panel de Control de Cierres
        st.subheader("📊 Panel de Control de Cierres")
        col1, col2 = st.columns(2)
        
        with col1:
            total_cerrados = len(data[data['FechaPre'].notna()])
            st.metric(
                "Total Expedientes Cerrados",
                f"{total_cerrados:,d}",
                help="Número total de expedientes que han sido cerrados"
            )
        
        with col2:
            # Calcular tiempos de cierre más representativos
            tiempos_cierre = (data['FechaPre'] - data['FechaExpendiente']).dt.days
            
            # Eliminar outliers usando el método IQR
            Q1 = tiempos_cierre.quantile(0.25)
            Q3 = tiempos_cierre.quantile(0.75)
            IQR = Q3 - Q1
            tiempos_filtrados = tiempos_cierre[
                (tiempos_cierre >= Q1 - 1.5 * IQR) & 
                (tiempos_cierre <= Q3 + 1.5 * IQR)
            ]
            
            tiempo_promedio = tiempos_filtrados.median()  # Usar mediana en lugar de media
            percentil_80 = tiempos_filtrados.quantile(0.8)
            
            st.metric(
                "Tiempo Típico de Cierre",
                f"{tiempo_promedio:.1f} días",
                f"80% se cierra en {percentil_80:.1f} días o menos",
                help="Tiempo típico de cierre (excluyendo casos extremos)"
            )

        # 2. Selección del rango de fechas
        st.markdown("---")
        st.subheader("📅 Matriz de Cierre por Período")
        
        range_options = {
            "Últimos 15 días": 15,
            "Últimos 30 días": 30,
            "Durante el último mes": "month"
        }
        
        selected_range = st.radio(
            "Seleccionar Período de Análisis",
            options=list(range_options.keys()),
            horizontal=True
        )

        # Determinar el rango de fechas basado en la selección
        if selected_range == "Durante el último mes":
            date_threshold = pd.Timestamp.now().replace(day=1)
        else:
            days = range_options[selected_range]
            date_threshold = pd.Timestamp.now() - pd.DateOffset(days=days)

        cierre_data_range = data[data['FechaPre'] >= date_threshold].copy()

        # Calcular 'TiempoCierre'
        cierre_data_range['TiempoCierre'] = (cierre_data_range['FechaPre'] - cierre_data_range['FechaExpendiente']).dt.days

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

        # Calcular el promedio dinámico de cierre por evaluador
        def calcular_promedio_dias_validos(cierre_data):
            # Contar cierres por día
            cierres_por_dia = cierre_data.groupby(['EVALASIGN', 'FechaPre']).size().reset_index(name='Cierres')

            # Agregar columna del día de la semana
            cierres_por_dia['DiaSemana'] = cierres_por_dia['FechaPre'].dt.dayofweek  # 0 = Lunes, 6 = Domingo

            # Filtrar días válidos
            cierres_por_dia['Valido'] = (
                (cierres_por_dia['DiaSemana'].between(0, 4)) |  # Lunes a Viernes
                ((cierres_por_dia['DiaSemana'] == 5) & (cierres_por_dia['Cierres'] > 10)) |  # Sábados con > 10 cierres
                ((cierres_por_dia['DiaSemana'] == 6) & (cierres_por_dia['Cierres'] > 10))    # Domingos con > 10 cierres
            )

            # Filtrar solo días válidos
            dias_validos = cierres_por_dia[cierres_por_dia['Valido'] & (cierres_por_dia['Cierres'] > 0)]

            # Calcular promedio dinámico por evaluador
            promedio_por_evaluador = dias_validos.groupby('EVALASIGN').apply(
                lambda x: x['Cierres'].sum() / x['FechaPre'].nunique()
            ).reset_index(name='PromedioDíasCierre')

            return promedio_por_evaluador

        tiempo_promedio_por_evaluador = calcular_promedio_dias_validos(cierre_data_range)

        # Mostrar el tiempo promedio general
        tiempo_promedio_general = tiempo_promedio_por_evaluador['PromedioDíasCierre'].mean()
        st.metric(f"Tiempo Promedio General de Cierre ({selected_range})", f"{tiempo_promedio_general:.2f} días")

        # Ordenar la matriz por promedio de cierre dinámico
        cierre_matrix['Promedio'] = cierre_matrix.index.map(
            tiempo_promedio_por_evaluador.set_index('EVALASIGN')['PromedioDíasCierre'].to_dict()
        )
        cierre_matrix = cierre_matrix.sort_values(by='Promedio', ascending=False)

        # Mostrar la matriz en Streamlit
        st.subheader(f"Matriz de Cierre de Expedientes ({selected_range})")
        st.dataframe(cierre_matrix)

        # Mostrar tabla de tiempos promedio real por evaluador (tiempo entre fechas)
        st.subheader(f"Tiempos Promedio de Cierre por Evaluador ({selected_range})")
        tiempo_promedio_real = cierre_data_range.groupby('EVALASIGN')['TiempoCierre'].agg(
            TiempoPromedio=lambda x: x.mean()
        ).reset_index()
        
        st.dataframe(
            tiempo_promedio_real
            .sort_values(by='TiempoPromedio', ascending=True)  # Ordenar de menor a mayor tiempo
            .assign(TiempoPromedio=lambda x: x['TiempoPromedio'].round(2))
            .reset_index(drop=True)
        )

        # Nueva sección de distribución de tiempos
        st.subheader(f"📊 Distribución de Tiempos de Cierre ({selected_range})")
        
        # Calcular rangos más representativos
        tiempos_cierre_periodo = (cierre_data_range['FechaPre'] - cierre_data_range['FechaExpendiente']).dt.days
        
        # Definir rangos dinámicos basados en percentiles
        percentiles = [0, 25, 50, 75, 90, 95]  # Quitamos el 100 para que coincida con las etiquetas
        rangos = np.percentile(tiempos_cierre_periodo, percentiles)
        
        # Crear etiquetas personalizadas (una menos que los bins)
        labels = [
            f"Muy rápido (0-{rangos[1]:.0f} días)",
            f"Rápido ({rangos[1]:.0f}-{rangos[2]:.0f} días)",
            f"Normal ({rangos[2]:.0f}-{rangos[3]:.0f} días)",
            f"Demorado ({rangos[3]:.0f}-{rangos[4]:.0f} días)",
            f"Casos especiales (>{rangos[4]:.0f} días)"
        ]
        
        # Categorizar los tiempos (bins debe tener un elemento más que labels)
        bins = [float('-inf')] + list(rangos)[1:] + [float('inf')]
        cierre_data_range['CategoríaTiempo'] = pd.cut(
            tiempos_cierre_periodo,
            bins=bins,
            labels=labels,
            include_lowest=True
        )

        # Calcular distribución
        distribucion_tiempos = cierre_data_range['CategoríaTiempo'].value_counts(normalize=True) * 100

        # Crear gráfico de distribución
        fig_tiempos = px.bar(
            distribucion_tiempos,
            title=f"Distribución de Tiempos de Cierre ({selected_range})",
            labels={'index': "Categoría", 'value': "Porcentaje de Expedientes"},
            text=distribucion_tiempos.round(1).astype(str) + '%',
            color_discrete_sequence=['#2ecc71', '#3498db', '#f1c40f', '#e67e22', '#e74c3c']
        )
        
        fig_tiempos.update_traces(textposition='outside')
        st.plotly_chart(fig_tiempos, use_container_width=True)

        st.info("""
        📌 **Interpretación de las Categorías:**
        - **Muy rápido**: El 25% más rápido de los cierres
        - **Rápido**: Entre el percentil 25 y la mediana
        - **Normal**: Entre la mediana y el percentil 75
        - **Demorado**: Entre el percentil 75 y 90
        - **Casos especiales**: Más del percentil 90 (pueden requerir atención especial)
        """)

        # Nueva sección: Top 25 expedientes más demorados
        st.subheader(f"Top 25 Expedientes con Mayor Tiempo de Cierre ({selected_range})")
        
        # Preparar datos para el top 25
        top_25_demorados = (
            cierre_data_range[['NumeroTramite', 'EVALASIGN', 'FechaExpendiente', 'FechaPre', 'FECHA DE TRABAJO', 'TiempoCierre']]
            .sort_values('TiempoCierre', ascending=False)
            .head(25)
            .assign(
                FechaExpendiente=lambda x: x['FechaExpendiente'].dt.strftime('%d/%m/%Y'),
                FechaPre=lambda x: x['FechaPre'].dt.strftime('%d/%m/%Y'),
                FechaTrabajo=lambda x: x['FECHA DE TRABAJO'].dt.strftime('%d/%m/%Y'),
                TiempoCierre=lambda x: x['TiempoCierre'].round(2)
            )
            .rename(columns={
                'NumeroTramite': 'N° Expediente',
                'EVALASIGN': 'Evaluador',
                'FechaExpendiente': 'Fecha Ingreso',
                'FechaPre': 'Fecha Cierre',
                'FechaTrabajo': 'Fecha Trabajo',
                'TiempoCierre': 'Días Transcurridos'
            })
            .drop(columns=['FECHA DE TRABAJO'])
        )
        
        st.dataframe(top_25_demorados)

        # Opción para descargar el top 25
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            top_25_demorados.to_excel(writer, index=False, sheet_name="Top 25 Más Demorados")
        output.seek(0)
        
        st.download_button(
            label="Descargar Top 25 Expedientes Más Demorados",
            data=output,
            file_name=f"top_25_demorados_{selected_range.lower().replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ) 
    except Exception as e:
        st.error(f"Error al procesar la pestaña de cierre de expedientes: {e}") 