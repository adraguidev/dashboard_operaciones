import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import numpy as np
from src.utils.excel_utils import create_excel_download

def render_closing_analysis_tab(data: pd.DataFrame):
    try:
        st.header("🎯 Análisis de Cierre de Expedientes")
        
        # Verificar que las columnas necesarias existen
        required_columns = ['FechaPre', 'FechaExpendiente', 'ESTADO', 'Evaluado']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            st.error(f"Faltan las siguientes columnas necesarias: {', '.join(missing_columns)}")
            return

        # Crear una copia del DataFrame para no modificar el original
        data = data.copy()

        # Convertir columnas categóricas a string y asegurar que no sean categóricas
        categorical_columns = ['ESTADO', 'Evaluado', 'EVALASIGN', 'DESCRIPCION']
        for col in categorical_columns:
            if col in data.columns:
                if pd.api.types.is_categorical_dtype(data[col]):
                    data[col] = data[col].astype(str)
                elif isinstance(data[col], pd.Series):
                    data[col] = data[col].fillna('').astype(str)

        # Asegurar que las fechas son válidas
        data['FechaPre'] = pd.to_datetime(data['FechaPre'], errors='coerce')
        data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'], errors='coerce')
        if 'FECHA DE TRABAJO' in data.columns:
            data['FECHA DE TRABAJO'] = pd.to_datetime(data['FECHA DE TRABAJO'], errors='coerce')
        
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
            # Filtrar solo expedientes del último año y creados en el mismo año
            ultimo_anio = pd.Timestamp.now() - pd.DateOffset(years=1)
            expedientes_recientes = data[
                (data['FechaExpendiente'] >= ultimo_anio) & 
                (data['FechaPre'] >= ultimo_anio) &
                (data['FechaExpendiente'].dt.year == data['FechaPre'].dt.year)
            ]
            
            tiempos_cierre = (expedientes_recientes['FechaPre'] - expedientes_recientes['FechaExpendiente']).dt.days
            
            if not tiempos_cierre.empty:
                # Eliminar outliers usando el método IQR
                Q1 = tiempos_cierre.quantile(0.25)
                Q3 = tiempos_cierre.quantile(0.75)
                IQR = Q3 - Q1
                tiempos_filtrados = tiempos_cierre[
                    (tiempos_cierre >= Q1 - 1.5 * IQR) & 
                    (tiempos_cierre <= Q3 + 1.5 * IQR)
                ]
                
                if not tiempos_filtrados.empty:
                    tiempo_promedio = tiempos_filtrados.median()
                    percentil_80 = tiempos_filtrados.quantile(0.8)
                    percentil_90 = tiempos_filtrados.quantile(0.9)
                    
                    st.metric(
                        "Tiempo Típico de Cierre",
                        f"{tiempo_promedio:.1f} días",
                        f"90% se cierra en {percentil_90:.1f} días o menos",
                        help="Tiempo típico de cierre del último año (excluyendo casos extremos)"
                    )
                    
                    st.caption(f"""
                    📊 Distribución de tiempos:
                    - 25% se cierra en {Q1:.1f} días o menos
                    - 50% se cierra en {tiempo_promedio:.1f} días o menos
                    - 75% se cierra en {Q3:.1f} días o menos
                    - 90% se cierra en {percentil_90:.1f} días o menos
                    """)
                else:
                    st.warning("No hay suficientes datos para calcular estadísticas de tiempos de cierre.")
            else:
                st.warning("No hay datos de tiempos de cierre para el período seleccionado.")

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
            try:
                # Contar cierres por día
                cierres_por_dia = cierre_data.groupby(['EVALASIGN', 'FechaPre']).size().reset_index(name='Cierres')

                # Agregar columna del día de la semana como número
                cierres_por_dia['DiaSemana'] = cierres_por_dia['FechaPre'].dt.dayofweek  # 0 = Lunes, 6 = Domingo

                # Filtrar días válidos usando números en lugar de categorías
                dias_validos = cierres_por_dia[
                    ((cierres_por_dia['DiaSemana'] >= 0) & (cierres_por_dia['DiaSemana'] <= 4)) |  # Lunes a Viernes
                    ((cierres_por_dia['DiaSemana'] == 5) & (cierres_por_dia['Cierres'] > 10)) |  # Sábados con > 10 cierres
                    ((cierres_por_dia['DiaSemana'] == 6) & (cierres_por_dia['Cierres'] > 10))    # Domingos con > 10 cierres
                ]

                # Filtrar solo días con cierres
                dias_validos = dias_validos[dias_validos['Cierres'] > 0]

                if dias_validos.empty:
                    return pd.DataFrame(columns=['EVALASIGN', 'PromedioDíasCierre'])

                # Calcular promedio dinámico por evaluador
                promedio_por_evaluador = dias_validos.groupby('EVALASIGN').apply(
                    lambda x: x['Cierres'].sum() / x['FechaPre'].nunique()
                ).reset_index(name='PromedioDíasCierre')

                return promedio_por_evaluador
            except Exception as e:
                st.error(f"Error en calcular_promedio_dias_validos: {str(e)}")
                return pd.DataFrame(columns=['EVALASIGN', 'PromedioDíasCierre'])

        tiempo_promedio_por_evaluador = calcular_promedio_dias_validos(cierre_data_range)

        if not tiempo_promedio_por_evaluador.empty:
            # Mostrar el tiempo promedio general
            tiempo_promedio_general = tiempo_promedio_por_evaluador['PromedioDíasCierre'].mean()
            st.metric(f"Tiempo Promedio General de Cierre ({selected_range})", f"{tiempo_promedio_general:.2f} días")

            # Ordenar la matriz por promedio de cierre dinámico
            cierre_matrix['Promedio'] = cierre_matrix.index.map(
                tiempo_promedio_por_evaluador.set_index('EVALASIGN')['PromedioDíasCierre'].to_dict()
            ).fillna(0)  # Llenar NaN con 0
            cierre_matrix = cierre_matrix.sort_values(by='Promedio', ascending=False)

            # Mostrar la matriz en Streamlit
            st.subheader(f"Matriz de Cierre de Expedientes ({selected_range})")
            st.dataframe(cierre_matrix)

            # Agregar botón de descarga formateado para la matriz de cierre
            excel_data_matriz = create_excel_download(
                cierre_matrix,
                "matriz_cierre.xlsx",
                "Matriz_Cierre",
                f"Matriz de Cierre de Expedientes - {selected_range}"
            )
            
            st.download_button(
                label="📥 Descargar Matriz de Cierre",
                data=excel_data_matriz,
                file_name=f"matriz_cierre_{selected_range.lower().replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

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
        else:
            st.warning("No hay datos suficientes para calcular los promedios de cierre.")

        # Nueva sección de distribución de tiempos
        st.subheader(f"📊 Distribución de Tiempos de Cierre ({selected_range})")
        
        if not cierre_data_range.empty:
            # Definir rangos de tiempo y sus etiquetas
            rangos = [
                (0, 3), (4, 6), (7, 9), (10, 12), (13, 15),
                (16, 18), (19, 21), (22, 24), (25, 28)
            ]
            
            # Función para asignar etiqueta según el tiempo
            def asignar_rango(tiempo):
                if tiempo > 28:
                    return "28+ días"
                for min_dias, max_dias in rangos:
                    if min_dias <= tiempo <= max_dias:
                        return f"{min_dias}-{max_dias} días"
                return "28+ días"  # Por defecto si no cae en ningún rango
            
            # Crear una serie con los rangos
            cierre_data_range['RangoTiempo'] = cierre_data_range['TiempoCierre'].apply(asignar_rango)
            
            # Calcular la distribución
            distribucion = cierre_data_range['RangoTiempo'].value_counts()
            
            # Calcular porcentajes
            total = len(cierre_data_range)
            distribucion_porcentaje = (distribucion / total * 100).round(1)
            
            # Ordenar los rangos correctamente
            orden_rangos = [f"{min_dias}-{max_dias} días" for min_dias, max_dias in rangos] + ["28+ días"]
            distribucion_porcentaje = distribucion_porcentaje.reindex(orden_rangos).fillna(0)

            # Crear gráfico de distribución de tiempos mejorado
            fig_tiempos = px.bar(
                distribucion_porcentaje,
                title=f"Distribución de Tiempos de Cierre ({selected_range})",
                labels={'index': "Tiempo de Cierre", 'value': "Porcentaje de Expedientes"},
                text=distribucion_porcentaje.round(1).astype(str) + '%',
                color_discrete_sequence=['#2ecc71', '#3498db', '#f1c40f', '#e67e22', '#e74c3c', 
                                       '#9b59b6', '#1abc9c', '#34495e', '#95a5a6', '#d35400']
            )

            fig_tiempos.update_traces(textposition='outside')
            fig_tiempos.update_layout(
                showlegend=False,
                xaxis_title="Rango de Días",
                yaxis_title="Porcentaje de Expedientes (%)",
                bargap=0.2
            )

            st.plotly_chart(fig_tiempos, use_container_width=True)

            st.info("""
            📌 **Interpretación de los Rangos:**
            - Los expedientes que se cierran en 1-6 días muestran una gestión muy eficiente
            - El rango de 7-15 días representa el tiempo de procesamiento estándar
            - Expedientes que toman más de 15 días pueden requerir atención especial
            - Casos de más de 28 días generalmente indican complejidades adicionales
            """)

            # Nueva sección: Top 25 expedientes más demorados
            if 'NumeroTramite' in cierre_data_range.columns:
                st.subheader(f"Top 25 Expedientes con Mayor Tiempo de Cierre ({selected_range})")
                
                # Preparar datos para el top 25
                top_25_demorados = (
                    cierre_data_range[['NumeroTramite', 'EVALASIGN', 'FechaExpendiente', 'FechaPre', 'FECHA DE TRABAJO', 'TiempoCierre']]
                    .sort_values('TiempoCierre', ascending=False)
                    .head(25)
                    .assign(
                        FechaExpendiente=lambda x: x['FechaExpendiente'].dt.strftime('%d/%m/%Y'),
                        FechaPre=lambda x: x['FechaPre'].dt.strftime('%d/%m/%Y'),
                        FechaTrabajo=lambda x: pd.to_datetime(x['FECHA DE TRABAJO']).dt.strftime('%d/%m/%Y'),
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

                # Agregar botón de descarga formateado
                excel_data = create_excel_download(
                    top_25_demorados,
                    "top_25_demorados.xlsx",
                    "Top_25_Demorados",
                    f"Top 25 Expedientes Más Demorados - {selected_range}"
                )
                
                st.download_button(
                    label="📥 Descargar Top 25 Expedientes Demorados",
                    data=excel_data,
                    file_name=f"top_25_demorados_{selected_range.lower().replace(' ', '_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("No hay datos de cierre para el período seleccionado.")

    except Exception as e:
        st.error(f"Error al procesar la pestaña de cierre de expedientes: {str(e)}")
        print(f"Error detallado en closing_analysis: {str(e)}") 