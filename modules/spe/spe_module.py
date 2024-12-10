import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from google.oauth2 import service_account
import gspread
import pymongo
from datetime import datetime, timedelta
from config.spe_config import SPE_SETTINGS
from src.utils.database import get_google_credentials
from config.settings import INACTIVE_EVALUATORS, MONGODB_CONFIG
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid.shared import JsCode
import numpy as np
import plotly.graph_objects as go
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from statsmodels.nonparametric.smoothers_lowess import lowess
from prophet import Prophet
from src.utils.excel_utils import create_excel_download

class SPEModule:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self):
        """Inicializar módulo SPE."""
        self.credentials = get_google_credentials()
        # Inicializar variable para datos
        if 'spe_data' not in st.session_state:
            st.session_state.spe_data = None

    def load_data(self):
        """Cargar datos desde Google Sheets."""
        try:
            # Si los datos ya están en session_state y no se solicitó recarga, usarlos
            if st.session_state.spe_data is not None:
                return st.session_state.spe_data

            if self.credentials is None:
                st.error("No se pudo inicializar el cliente de Google Sheets")
                return None
                
            sheet = gspread.authorize(self.credentials).open_by_key(SPE_SETTINGS['SPREADSHEET_ID']).worksheet(SPE_SETTINGS['WORKSHEET_NAME'])
            # Cargar datos y guardarlos en session_state
            data = pd.DataFrame(sheet.get_all_records())
            st.session_state.spe_data = data
            return data
        except Exception as e:
            st.error(f"Error al cargar datos de Google Sheets: {str(e)}")
            return None

    def render_module(self):
        """Renderizar el módulo SPE."""
        # Botón para recargar datos en la parte superior del módulo
        col1, col2 = st.columns([1, 11])
        with col1:
            if st.button("🔄 Recargar Datos", key="reload_spe_data_main"):
                # Limpiar todas las claves de caché que contengan 'spe'
                for key in st.session_state.keys():
                    if 'spe' in key.lower():
                        del st.session_state[key]
                st.cache_resource.clear()
                st.cache_data.clear()
                st.rerun()

        data = self.load_data()
        if data is None:
            return

        # Inicializar conexión MongoDB
        client = self._init_mongodb_connection()
        db = client[MONGODB_CONFIG['database']]
        collection = db[MONGODB_CONFIG['collections']['rankings']]

        tabs = st.tabs([
            "Reporte de Pendientes", 
            "Reporte de Trabajados",
            "Ranking de Expedientes Trabajados",
            "Análisis Dinámico",
            "Predicción de Ingresos"  # Nueva pestaña
        ])
        
        with tabs[0]:
            self.render_pending_report(data)
        with tabs[1]:
            self.render_worked_report(data)
        with tabs[2]:
            self.render_ranking_report(data, collection)
        with tabs[3]:
            self.render_dynamic_analysis(data)
        with tabs[4]:
            self.render_predictive_analysis(data)  # Nuevo método

    @staticmethod
    @st.cache_resource
    def _init_mongodb_connection():
        """Inicializar conexión a MongoDB."""
        return pymongo.MongoClient(st.secrets["connections"]["mongodb"]["uri"])

    def render_ranking_report(self, data, collection):
        """Renderizar pestaña de ranking de expedientes trabajados."""
        st.header("Ranking de Expedientes Trabajados")

        COLUMNAS = {
            'EVALUADOR': 'EVALUADOR',
            'EXPEDIENTE': 'EXPEDIENTE',
            'FECHA_TRABAJO': 'Fecha_Trabajo'
        }

        # Usar timezone de Peru para las fechas
        fecha_actual = pd.Timestamp.now(tz='America/Lima')
        fecha_ayer = (fecha_actual - pd.Timedelta(days=1)).date()

        # Convertir fecha de trabajo a datetime de manera más segura
        try:
            # Primero limpiar valores no válidos
            data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
                data[COLUMNAS['FECHA_TRABAJO']].replace(['', 'NaT', 'NaN', 'nat'], pd.NaT), 
                format='mixed',
                dayfirst=True,
                errors='coerce'
            )
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return

        # Filtrar filas con fechas válidas antes de procesar
        data = data[data[COLUMNAS['FECHA_TRABAJO']].notna()]

        # Obtener última fecha registrada
        ultima_fecha_db = self._get_last_date_from_db(collection)
        ultima_fecha = ultima_fecha_db.date() if ultima_fecha_db else None

        if ultima_fecha:
            st.info(f"📅 Último registro guardado: {ultima_fecha.strftime('%d/%m/%Y')}")

        # Obtener datos históricos de MongoDB
        registros_historicos = list(collection.find({
            "modulo": "SPE",
            "fecha": {"$lt": fecha_actual}
        }).sort("fecha", -1))

        # Preparar DataFrame histórico
        df_historico = pd.DataFrame()
        fechas_guardadas = set()

        # Procesar registros históricos
        if registros_historicos:
            for registro in registros_historicos:
                fecha = pd.Timestamp(registro['fecha'])
                fechas_guardadas.add(fecha.date())
                fecha_str = fecha.strftime('%d/%m')
                df_temp = pd.DataFrame(registro['datos'])
                if not df_temp.empty:
                    evaluador_col = 'EVALUADOR' if 'EVALUADOR' in df_temp.columns else 'evaluador'
                    df_pivot = pd.DataFrame({
                        'EVALUADOR': df_temp[evaluador_col].tolist(),
                        fecha_str: df_temp['cantidad'].tolist()
                    })
                    if df_historico.empty:
                        df_historico = df_pivot
                    else:
                        df_historico = df_historico.merge(
                            df_pivot, on='EVALUADOR', how='outer'
                        )

        # Procesar datos nuevos del Google Sheets que aún no están en la BD
        datos_nuevos = data[
            (data[COLUMNAS['FECHA_TRABAJO']].notna()) &  # Asegurar que la fecha es válida
            (data[COLUMNAS['EVALUADOR']].notna()) &
            (data[COLUMNAS['EVALUADOR']] != '')
        ].copy()

        # Asegurar que las fechas son datetime antes de agrupar
        if not datos_nuevos.empty:
            try:
                # Agrupar datos nuevos por fecha y evaluador
                datos_nuevos_agrupados = datos_nuevos.groupby([
                    datos_nuevos[COLUMNAS['FECHA_TRABAJO']].dt.date,
                    COLUMNAS['EVALUADOR']
                ]).size().reset_index(name='cantidad')

                # Agregar datos nuevos al DataFrame histórico
                for fecha in datos_nuevos_agrupados[COLUMNAS['FECHA_TRABAJO']].unique():
                    if fecha not in fechas_guardadas and fecha <= fecha_ayer:
                        fecha_str = pd.Timestamp(fecha).strftime('%d/%m')
                        datos_fecha = datos_nuevos_agrupados[
                            datos_nuevos_agrupados[COLUMNAS['FECHA_TRABAJO']] == fecha
                        ]
                        df_pivot = pd.DataFrame({
                            'EVALUADOR': datos_fecha[COLUMNAS['EVALUADOR']].tolist(),
                            fecha_str: datos_fecha['cantidad'].tolist()
                        })
                        
                        if df_historico.empty:
                            df_historico = df_pivot
                        else:
                            df_historico = df_historico.merge(
                                df_pivot, on='EVALUADOR', how='outer'
                            )
            except Exception as e:
                st.error(f"Error al procesar datos nuevos: {str(e)}")

        # Identificar columnas con datos no guardados
        columnas_no_guardadas = []
        for col in cols_fecha:
            try:
                # Intentar convertir la fecha agregando el año actual
                fecha_col = pd.to_datetime(
                    col + f"/{datetime.now().year}", 
                    format="%d/%m/%Y",
                    errors='coerce'
                )
                if fecha_col is not pd.NaT and fecha_col.date() not in fechas_guardadas:
                    columnas_no_guardadas.append(col)
            except Exception:
                # Si hay error en el formato, intentar otros formatos comunes
                try:
                    # Limpiar el string de fecha
                    fecha_str = col.strip().replace('_x', '')
                    fecha_col = pd.to_datetime(
                        fecha_str + f"/{datetime.now().year}",
                        format="%d/%m/%Y",
                        errors='coerce'
                    )
                    if fecha_col is not pd.NaT and fecha_col.date() not in fechas_guardadas:
                        columnas_no_guardadas.append(col)
                except Exception as e:
                    st.error(f"Error al procesar la fecha {col}: {str(e)}")
                    continue

        # Mostrar datos pendientes de guardar
        fechas_pendientes = []
        try:
            fechas_pendientes = sorted(set(
                fecha for fecha in datos_nuevos_agrupados[COLUMNAS['FECHA_TRABAJO']].unique()
                if fecha not in fechas_guardadas and fecha <= fecha_ayer
            ))
        except Exception as e:
            st.error(f"Error al procesar fechas pendientes: {str(e)}")

        if fechas_pendientes:
            st.warning("⚠️ Hay datos pendientes por guardar de las siguientes fechas:")
            for fecha in fechas_pendientes:
                try:
                    st.write(f"- {fecha.strftime('%d/%m/%Y')}")
                except Exception as e:
                    st.error(f"Error al mostrar fecha pendiente: {str(e)}")
            st.write("Las columnas resaltadas en amarillo contienen datos no guardados.")

        # Aplicar estilo al DataFrame para resaltar columnas no guardadas
        def highlight_cols(col):
            if col in columnas_no_guardadas:
                return ['background-color: #ffeb3b'] * len(df_historico)
            return [''] * len(df_historico)
        
        try:
            # Mostrar DataFrame con estilo
            st.dataframe(
                df_historico.style.apply(highlight_cols, subset=columnas_no_guardadas),
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error al mostrar tabla con estilos: {str(e)}")
            # Mostrar DataFrame sin estilos como fallback
            st.dataframe(df_historico, use_container_width=True)

        # Agregar botón de descarga formateado
        excel_data_ranking = create_excel_download(
            df_historico,
            "ranking_expedientes.xlsx",
            "Ranking_Expedientes",
            "Ranking de Expedientes Trabajados"
        )
        
        st.download_button(
            label="📥 Descargar Ranking",
            data=excel_data_ranking,
            file_name="ranking_expedientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Botones de acción
        col1, col2 = st.columns(2)

        with col1:
            if ultima_fecha_db:
                if st.button("🔄 Resetear último día", key="resetear_fecha"):
                    try:
                        collection.delete_many({
                            "modulo": "SPE",
                            "fecha": ultima_fecha_db
                        })
                        st.success("✅ Última fecha eliminada correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al resetear la última fecha: {str(e)}")

        with col2:
            if not datos_nuevos.empty:
                # Mostrar fechas disponibles para guardar
                fechas_disponibles = sorted(
                    datos_nuevos[COLUMNAS['FECHA_TRABAJO']].dt.date.unique()
                )
                
                if fechas_disponibles:
                    st.warning("⚠️ Hay fechas pendientes por guardar")
                    selected_dates = st.multiselect(
                        "Seleccionar fechas para guardar",
                        options=fechas_disponibles,
                        default=fechas_disponibles,
                        format_func=lambda x: x.strftime('%d/%m/%Y')
                    )
                    
                    if selected_dates and st.button("💾 Guardar datos seleccionados"):
                        try:
                            for fecha in selected_dates:
                                datos_dia = datos_nuevos[
                                    datos_nuevos[COLUMNAS['FECHA_TRABAJO']].dt.date == fecha
                                ]
                                datos_agrupados = datos_dia.groupby(COLUMNAS['EVALUADOR']).size().reset_index(name='cantidad')
                                
                                nuevo_registro = {
                                    "fecha": pd.Timestamp(fecha),
                                    "datos": datos_agrupados.to_dict('records'),
                                    "modulo": "SPE"
                                }
                                collection.insert_one(nuevo_registro)
                            
                            st.success("✅ Datos guardados correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar los datos: {str(e)}")

    def _get_last_date_from_db(self, collection):
        """Obtener la última fecha registrada en la base de datos."""
        fecha_actual = pd.Timestamp.now(tz='America/Lima').date()
        
        # Buscar el último registro que NO sea del día actual
        ultimo_registro = collection.find_one(
            {
                "modulo": "SPE",
                "fecha": {"$lt": pd.Timestamp(fecha_actual, tz='America/Lima')}
            }, 
            sort=[("fecha", -1)]
        )
        return ultimo_registro['fecha'] if ultimo_registro else None

    def render_pending_report(self, data):
        """Renderizar reporte de pendientes."""
        st.header("Reporte de Pendientes")

        # Mapeo de nombres de columnas con los nombres reales del Google Sheet
        COLUMNAS = {
            'EVALUADOR': 'EVALUADOR',
            'EXPEDIENTE': 'EXPEDIENTE',
            'ETAPA': 'ETAPA_EVALUACIÓN',
            'ESTADO': 'ESTADO',
            'FECHA_INGRESO': 'FECHA _ INGRESO',
            'FECHA_TRABAJO': 'Fecha_Trabajo'
        }

        # Limpiar datos innecesarios
        data = data.drop(['Column 12', 'Column 13', 'Column 14', 'Column 15', 'Column 16', 'Column 17'], axis=1)

        # Filtrar solo expedientes pendientes (INICIADA o en blanco)
        data_filtrada = data[
            data[COLUMNAS['ETAPA']].isin(["", "INICIADA"]) | 
            data[COLUMNAS['ETAPA']].isna()
        ]

        # 1. TABLA DE EVALUADORES
        st.subheader("Pendientes por Evaluador")
        
        pivot_table = pd.pivot_table(
            data_filtrada,
            index=COLUMNAS['EVALUADOR'],
            values=COLUMNAS['EXPEDIENTE'],
            aggfunc='nunique',
            margins=True,
            margins_name='Total'
        )
        pivot_table.columns = ['Cantidad de Expedientes']

        # Ordenar excluyendo total
        total_row = pivot_table.loc[['Total']]
        rest_of_data = pivot_table.drop('Total')
        rest_of_data = rest_of_data.sort_values(by='Cantidad de Expedientes', ascending=False)
        pivot_table = pd.concat([rest_of_data, total_row])

        st.dataframe(
            pivot_table,
            use_container_width=True,
            height=400
        )

        # Agregar botón de descarga formateado
        excel_data_evaluador = create_excel_download(
            pivot_table,
            "pendientes_evaluador.xlsx",
            "Pendientes_Evaluador",
            "Pendientes por Evaluador"
        )
        
        st.download_button(
            label="📥 Descargar Pendientes por Evaluador",
            data=excel_data_evaluador,
            file_name="pendientes_evaluador.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 2. GRÁFICO DE EVALUADORES
        if len(pivot_table) > 1:
            fig = px.bar(
                pivot_table.reset_index().iloc[:-1],
                x=COLUMNAS['EVALUADOR'],
                y='Cantidad de Expedientes',
                title="Distribución de Expedientes Pendientes por Evaluador",
                text_auto=True
            )
            fig.update_traces(textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        # 3. TABLA DE ESTADOS
        st.subheader("Pendientes por Estado")
        
        data_iniciados = data_filtrada[data_filtrada[COLUMNAS['ETAPA']] == "INICIADA"]
        pivot_table_estado = pd.pivot_table(
            data_iniciados,
            index=COLUMNAS['ESTADO'],
            values=COLUMNAS['EXPEDIENTE'],
            aggfunc='nunique',
            margins=True,
            margins_name='Total'
        )
        pivot_table_estado.columns = ['Cantidad de Expedientes']

        # Ordenar excluyendo total
        total_row_estado = pivot_table_estado.loc[['Total']]
        rest_of_data_estado = pivot_table_estado.drop('Total')
        rest_of_data_estado = rest_of_data_estado.sort_values(by='Cantidad de Expedientes', ascending=False)
        pivot_table_estado = pd.concat([rest_of_data_estado, total_row_estado])

        st.dataframe(
            pivot_table_estado,
            use_container_width=True,
            height=400
        )

        # Agregar botón de descarga formateado
        excel_data_estado = create_excel_download(
            pivot_table_estado,
            "pendientes_estado.xlsx",
            "Pendientes_Estado",
            "Pendientes por Estado"
        )
        
        st.download_button(
            label="📥 Descargar Pendientes por Estado",
            data=excel_data_estado,
            file_name="pendientes_estado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # 4. GRÁFICO DE ESTADOS
        if len(pivot_table_estado) > 1:
            fig_estado = px.bar(
                pivot_table_estado.reset_index().iloc[:-1],
                x=COLUMNAS['ESTADO'],
                y='Cantidad de Expedientes',
                title="Distribución de Expedientes Pendientes por Estado",
                text_auto=True
            )
            fig_estado.update_traces(textposition='outside')
            st.plotly_chart(fig_estado, use_container_width=True)

        # BOTÓN DE DESCARGA AL FINAL
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pivot_table.to_excel(writer, sheet_name='Expedientes_Por_Evaluador')
            pivot_table_estado.to_excel(writer, sheet_name='Expedientes_Por_Estado')
            
            detalle = data_filtrada[[
                COLUMNAS['EXPEDIENTE'], 
                COLUMNAS['EVALUADOR'], 
                COLUMNAS['ETAPA'],
                COLUMNAS['ESTADO'],
                COLUMNAS['FECHA_INGRESO']
            ]].sort_values([COLUMNAS['EVALUADOR'], COLUMNAS['FECHA_INGRESO']])
            detalle.to_excel(writer, sheet_name='Detalle_Expedientes', index=False)
        output.seek(0)

        st.download_button(
            label="Descargar Reporte Completo",
            data=output,
            file_name=f"reporte_expedientes_pendientes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def render_worked_report(self, data):
        """Renderizar reporte de expedientes trabajados."""
        st.header("Reporte de Expedientes Trabajados")

        # Mapeo de columnas
        COLUMNAS = {
            'EVALUADOR': 'EVALUADOR',
            'EXPEDIENTE': 'EXPEDIENTE',
            'FECHA_TRABAJO': 'Fecha_Trabajo'
        }

        # Mapeo de meses a español
        MESES = {
            1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
            5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
            9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
        }

        # Convertir fecha de trabajo a datetime de manera más flexible
        try:
            data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
                data[COLUMNAS['FECHA_TRABAJO']], 
                format='mixed',  # Usar formato mixto para mayor flexibilidad
                dayfirst=True,   # Indicar que el día va primero
                errors='coerce'
            )
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return

        # Obtener mes anterior y mes actual
        fecha_actual = pd.Timestamp.now()
        mes_anterior = (fecha_actual - pd.DateOffset(months=1))
        
        # Función auxiliar para procesar datos por mes
        def procesar_datos_mes(fecha, datos):
            nombre_mes = MESES[fecha.month]
            
            # Filtrar registros del mes
            datos_mes = datos[
                (datos[COLUMNAS['FECHA_TRABAJO']].dt.month == fecha.month) &
                (datos[COLUMNAS['FECHA_TRABAJO']].dt.year == fecha.year)
            ].copy()

            # Agrupar por evaluador
            stats = datos_mes.groupby(COLUMNAS['EVALUADOR']).agg({
                COLUMNAS['EXPEDIENTE']: 'count',  # Total expedientes
                COLUMNAS['FECHA_TRABAJO']: lambda x: x.dt.date.nunique()  # Días únicos trabajados
            }).reset_index()

            # Renombrar columnas
            stats.columns = ['EVALUADOR', 'CANT_EXPEDIENTES', 'DIAS_TRABAJADOS']

            # Calcular promedio
            stats['PROMEDIO'] = (stats['CANT_EXPEDIENTES'] / stats['DIAS_TRABAJADOS']).round(0)

            # Ordenar y agregar ranking
            stats_ordenado = stats.sort_values('CANT_EXPEDIENTES', ascending=False)
            stats_ordenado.index = range(1, len(stats_ordenado) + 1)

            return stats_ordenado, nombre_mes

        # Procesar mes anterior
        stats_mes_anterior, nombre_mes_anterior = procesar_datos_mes(mes_anterior, data)

        # Mostrar tabla mes anterior
        st.subheader(f"Expedientes Trabajados - {nombre_mes_anterior} {mes_anterior.year}")
        st.dataframe(
            stats_mes_anterior,
            use_container_width=True,
            height=400
        )

        # Agregar botón de descarga formateado
        excel_data_anterior = create_excel_download(
            stats_mes_anterior,
            f"trabajados_{nombre_mes_anterior}.xlsx",
            f"Trabajados_{nombre_mes_anterior}",
            f"Expedientes Trabajados - {nombre_mes_anterior} {mes_anterior.year}"
        )
        
        st.download_button(
            label=f"���� Descargar Tabla {nombre_mes_anterior}",
            data=excel_data_anterior,
            file_name=f"trabajados_{nombre_mes_anterior}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Gráfico de tendencia diaria mes anterior
        datos_diarios_anterior = data[
            (data[COLUMNAS['FECHA_TRABAJO']].dt.month == mes_anterior.month) &
            (data[COLUMNAS['FECHA_TRABAJO']].dt.year == mes_anterior.year)
        ].groupby(COLUMNAS['FECHA_TRABAJO']).size().reset_index(name='cantidad')

        promedio_diario_anterior = datos_diarios_anterior['cantidad'].mean()

        fig_tendencia_anterior = px.line(
            datos_diarios_anterior,
            x=COLUMNAS['FECHA_TRABAJO'],
            y='cantidad',
            title=f'Tendencia Diaria - {nombre_mes_anterior} {mes_anterior.year}',
            labels={'cantidad': 'Expedientes Trabajados'}
        )
        # Agregar puntos y valores
        fig_tendencia_anterior.add_trace(go.Scatter(
            x=datos_diarios_anterior[COLUMNAS['FECHA_TRABAJO']],
            y=datos_diarios_anterior['cantidad'],
            mode='markers+text',
            text=datos_diarios_anterior['cantidad'],
            textposition='top center',
            name='Valores Diarios',
            showlegend=False
        ))
        fig_tendencia_anterior.add_hline(
            y=promedio_diario_anterior,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Promedio: {promedio_diario_anterior:.1f}"
        )
        st.plotly_chart(fig_tendencia_anterior, use_container_width=True)

        # Procesar mes actual
        stats_mes_actual, nombre_mes_actual = procesar_datos_mes(fecha_actual, data)

        # Mostrar tabla mes actual
        st.subheader(f"Expedientes Trabajados - {nombre_mes_actual} {fecha_actual.year}")
        st.dataframe(
            stats_mes_actual,
            use_container_width=True,
            height=400
        )

        # Agregar botón de descarga formateado
        excel_data_actual = create_excel_download(
            stats_mes_actual,
            f"trabajados_{nombre_mes_actual}.xlsx",
            f"Trabajados_{nombre_mes_actual}",
            f"Expedientes Trabajados - {nombre_mes_actual} {fecha_actual.year}"
        )
        
        st.download_button(
            label=f"📥 Descargar Tabla {nombre_mes_actual}",
            data=excel_data_actual,
            file_name=f"trabajados_{nombre_mes_actual}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Gráfico de tendencia diaria mes actual
        fecha_actual_sin_hora = fecha_actual.date()
        datos_diarios_actual = data[
            (data[COLUMNAS['FECHA_TRABAJO']].dt.month == fecha_actual.month) &
            (data[COLUMNAS['FECHA_TRABAJO']].dt.year == fecha_actual.year) &
            (data[COLUMNAS['FECHA_TRABAJO']].dt.date <= fecha_actual_sin_hora)
        ].groupby(COLUMNAS['FECHA_TRABAJO']).size().reset_index(name='cantidad')

        promedio_diario_actual = datos_diarios_actual['cantidad'].mean()

        fig_tendencia_actual = px.line(
            datos_diarios_actual,
            x=COLUMNAS['FECHA_TRABAJO'],
            y='cantidad',
            title=f'Tendencia Diaria - {nombre_mes_actual} {fecha_actual.year}',
            labels={'cantidad': 'Expedientes Trabajados'}
        )
        # Agregar puntos y valores
        fig_tendencia_actual.add_trace(go.Scatter(
            x=datos_diarios_actual[COLUMNAS['FECHA_TRABAJO']],
            y=datos_diarios_actual['cantidad'],
            mode='markers+text',
            text=datos_diarios_actual['cantidad'],
            textposition='top center',
            name='Valores Diarios',
            showlegend=False
        ))
        fig_tendencia_actual.add_hline(
            y=promedio_diario_actual,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Promedio: {promedio_diario_actual:.1f}"
        )
        st.plotly_chart(fig_tendencia_actual, use_container_width=True)

        # Análisis comparativo de rendimiento
        st.subheader("Análisis Comparativo de Rendimiento")
        
        col1, col2, col3 = st.columns(3)
        
        # Calcular días transcurridos primero
        fecha_actual_sin_hora = fecha_actual.date()
        dias_transcurridos = (fecha_actual_sin_hora - fecha_actual.replace(day=1).date()).days + 1

        # Variación en promedio diario
        variacion_promedio = ((promedio_diario_actual / promedio_diario_anterior) - 1) * 100
        with col1:
            st.metric(
                "Variación Promedio Diario",
                f"{promedio_diario_actual:.1f}",
                f"{variacion_promedio:+.1f}%",
                help="Comparación del promedio diario actual vs mes anterior"
            )

        # Eficiencia por evaluador
        with col2:
            promedio_evaluadores_anterior = stats_mes_anterior['PROMEDIO'].mean()
            promedio_evaluadores_actual = stats_mes_actual['PROMEDIO'].mean()
            var_eficiencia = ((promedio_evaluadores_actual / promedio_evaluadores_anterior) - 1) * 100
            st.metric(
                "Eficiencia Promedio por Evaluador",
                f"{promedio_evaluadores_actual:.1f}",
                f"{var_eficiencia:+.1f}%",
                help="Promedio de expedientes por día por evaluador"
            )

        # Productividad proporcional
        with col3:
            # Calcular productividad proporcional
            dias_mes_anterior = pd.Timestamp(mes_anterior.year, mes_anterior.month, 1).days_in_month
            prod_diaria_anterior = stats_mes_anterior['CANT_EXPEDIENTES'].sum() / dias_mes_anterior
            prod_esperada_actual = prod_diaria_anterior * dias_transcurridos
            prod_actual = stats_mes_actual['CANT_EXPEDIENTES'].sum()
            cumplimiento = (prod_actual / prod_esperada_actual) * 100
            
            st.metric(
                "Cumplimiento vs Mes Anterior",
                f"{prod_actual:,.0f} / {prod_esperada_actual:,.0f}",
                f"{cumplimiento-100:+.1f}%",
                help=f"Comparación proporcional considerando {dias_transcurridos} días transcurridos"
            )

        # Gráfico de distribución por evaluador
        fig_distribucion = px.pie(
            stats_mes_actual,
            values='CANT_EXPEDIENTES',
            names='EVALUADOR',
            title=f'Distribución de Expedientes por Evaluador - {nombre_mes_actual}'
        )
        st.plotly_chart(fig_distribucion, use_container_width=True)

        # Gráfico de promedio diario con comparativa
        comparativa_promedio = pd.merge(
            stats_mes_anterior[['EVALUADOR', 'PROMEDIO']].rename(columns={'PROMEDIO': f'Promedio {nombre_mes_anterior}'}),
            stats_mes_actual[['EVALUADOR', 'PROMEDIO']].rename(columns={'PROMEDIO': f'Promedio {nombre_mes_actual}'}),
            on='EVALUADOR',
            how='outer'
        ).fillna(0)

        fig_promedio = go.Figure()
        fig_promedio.add_trace(go.Bar(
            name=nombre_mes_anterior,
            x=comparativa_promedio['EVALUADOR'],
            y=comparativa_promedio[f'Promedio {nombre_mes_anterior}'],
            text=comparativa_promedio[f'Promedio {nombre_mes_anterior}'].round(1)
        ))
        fig_promedio.add_trace(go.Bar(
            name=nombre_mes_actual,
            x=comparativa_promedio['EVALUADOR'],
            y=comparativa_promedio[f'Promedio {nombre_mes_actual}'],
            text=comparativa_promedio[f'Promedio {nombre_mes_actual}'].round(1)
        ))
        
        fig_promedio.update_layout(
            title=f'Comparativa de Promedio Diario por Evaluador',
            barmode='group',
            yaxis_title="Promedio de Expedientes por Día"
        )
        fig_promedio.update_traces(textposition='outside')
        st.plotly_chart(fig_promedio, use_container_width=True)

        # Agregar comparativo anual 2024
        st.subheader("Comparativo Mensual 2024")

        # Preparar datos para todos los meses de 2024
        meses_2024 = []
        for mes in range(1, fecha_actual.month + 1):
            fecha_mes = pd.Timestamp(2024, mes, 1)
            stats_mes, nombre_mes = procesar_datos_mes(fecha_mes, data)
            
            # Calcular métricas de trabajo realizado
            datos_mes = data[
                (data[COLUMNAS['FECHA_TRABAJO']].dt.month == mes) &
                (data[COLUMNAS['FECHA_TRABAJO']].dt.year == 2024)
            ]
            
            dias_trabajados = datos_mes[COLUMNAS['FECHA_TRABAJO']].dt.date.nunique()
            total_trabajado = len(datos_mes)
            promedio_diario = total_trabajado / dias_trabajados if dias_trabajados > 0 else 0
            
            meses_2024.append({
                'Mes': nombre_mes,
                'Expedientes_Trabajados': total_trabajado,
                'Días_Trabajados': dias_trabajados,
                'Promedio_Diario': promedio_diario,
                'Cant_Evaluadores': len(stats_mes),
                'Promedio_Por_Evaluador': total_trabajado / len(stats_mes) if len(stats_mes) > 0 else 0
            })

        df_comparativo = pd.DataFrame(meses_2024)

        # Mostrar tabla comparativa
        st.dataframe(df_comparativo.style.format({
            'Promedio_Diario': '{:.1f}',
            'Promedio_Por_Evaluador': '{:.1f}',
            'Expedientes_Trabajados': '{:,.0f}'
        }), use_container_width=True)

        # Agregar botón de descarga formateado
        excel_data_comparativo = create_excel_download(
            df_comparativo,
            "comparativo_mensual_2024.xlsx",
            "Comparativo_Mensual_2024",
            "Comparativo Mensual 2024"
        )
        
        st.download_button(
            label="📥 Descargar Comparativo Mensual 2024",
            data=excel_data_comparativo,
            file_name="comparativo_mensual_2024.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Gráfico de tendencia mensual con dos ejes
        fig_tendencia_mensual = go.Figure()

        # Expedientes trabajados (barras)
        fig_tendencia_mensual.add_trace(go.Bar(
            name='Expedientes Trabajados',
            x=df_comparativo['Mes'],
            y=df_comparativo['Expedientes_Trabajados'],
            text=df_comparativo['Expedientes_Trabajados'].round(0),
            textposition='outside',
            yaxis='y'
        ))

        # Promedio diario (línea)
        fig_tendencia_mensual.add_trace(go.Scatter(
            name='Promedio Diario',
            x=df_comparativo['Mes'],
            y=df_comparativo['Promedio_Diario'],
            text=df_comparativo['Promedio_Diario'].round(1),
            textposition='top center',
            mode='lines+markers+text',
            yaxis='y2',
            line=dict(color='red')
        ))

        # Actualizar diseño
        fig_tendencia_mensual.update_layout(
            title='Evolución Mensual del Trabajo Realizado 2024',
            yaxis=dict(
                title='Total Expedientes Trabajados',
                titlefont=dict(color='blue'),
                tickfont=dict(color='blue')
            ),
            yaxis2=dict(
                title='Promedio Diario',
                titlefont=dict(color='red'),
                tickfont=dict(color='red'),
                overlaying='y',
                side='right'
            ),
            barmode='group',
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )

        st.plotly_chart(fig_tendencia_mensual, use_container_width=True)

        # Botón de descarga con ambos reportes
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Mes anterior
            stats_mes_anterior.to_excel(
                writer, 
                sheet_name=f'Estadisticas_{nombre_mes_anterior}_{mes_anterior.year}'
            )
            
            # Mes actual
            stats_mes_actual.to_excel(
                writer, 
                sheet_name=f'Estadisticas_{nombre_mes_actual}_{fecha_actual.year}'
            )
            
            # Detalles
            detalle = data[
                (data[COLUMNAS['FECHA_TRABAJO']].dt.month.isin([mes_anterior.month, fecha_actual.month])) &
                (data[COLUMNAS['FECHA_TRABAJO']].dt.year.isin([mes_anterior.year, fecha_actual.year]))
            ][[
                COLUMNAS['EXPEDIENTE'],
                COLUMNAS['EVALUADOR'],
                COLUMNAS['FECHA_TRABAJO']
            ]].sort_values([COLUMNAS['EVALUADOR'], COLUMNAS['FECHA_TRABAJO']])
            
            detalle.to_excel(
                writer, 
                sheet_name='Detalle_Expedientes',
                index=False
            )
        output.seek(0)

        st.download_button(
            label=f"Descargar Reporte {nombre_mes_anterior}-{nombre_mes_actual} {fecha_actual.year}",
            data=output,
            file_name=f"reporte_trabajados_{nombre_mes_anterior}_{nombre_mes_actual}_{fecha_actual.year}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def render_dynamic_analysis(self, data):
        """Renderizar análisis dinámico."""
        st.header("Análisis Dinámico")

        # Mapeo de columnas disponibles para filtrar
        COLUMNAS_FILTRO = {
            'EXPEDIENTE': 'EXPEDIENTE',
            'FECHA_ASIGNACION': 'FECHA_ASIGNACION',
            'PROCESO': 'PROCESO',
            'FECHA_INGRESO': 'FECHA _ INGRESO',
            'EVALUADOR': 'EVALUADOR',
            'ETAPA': 'ETAPA_EVALUACIÓN',
            'ESTADO': 'ESTADO',
            'FECHA_TRABAJO': 'Fecha_Trabajo',
            'BENEFICIARIO': 'NOMBRES_BENEFICIARIO'
        }

        # Convertir fechas a datetime
        for fecha_col in ['FECHA_ASIGNACION', 'FECHA_INGRESO', 'FECHA_TRABAJO']:
            try:
                data[COLUMNAS_FILTRO[fecha_col]] = pd.to_datetime(
                    data[COLUMNAS_FILTRO[fecha_col]], 
                    format='mixed',
                    dayfirst=True,
                    errors='coerce'
                )
            except Exception as e:
                st.error(f"Error al procesar fechas de {fecha_col}: {str(e)}")

        # Crear contenedor para filtros
        st.subheader("Filtros Dinámicos")
        
        # Usar expander para los filtros
        with st.expander("Mostrar/Ocultar Filtros", expanded=True):
            filtro_container = st.container()

            with filtro_container:
                # Selección de dimensiones para la tabla dinámica
                col1, col2 = st.columns(2)
                with col1:
                    columnas_filas = st.multiselect(
                        "Dimensiones para filas",
                        options=['EVALUADOR', 'PROCESO', 'ETAPA', 'ESTADO'],
                        default=['EVALUADOR']
                    )
                with col2:
                    columnas_columnas = st.multiselect(
                        "Dimensiones para columnas",
                        options=['PROCESO', 'ETAPA', 'ESTADO'],
                        default=['ESTADO']
                    )

                # Filtros de fecha
                st.subheader("Filtros de Fecha")
                fecha_cols = st.columns(3)
                
                # Filtro Fecha Asignación
                with fecha_cols[0]:
                    st.write("Fecha Asignación")
                    fecha_asig_inicio = st.date_input(
                        "Desde (Asignación)",
                        value=None,
                        key="fecha_asig_inicio"
                    )
                    fecha_asig_fin = st.date_input(
                        "Hasta (Asignación)",
                        value=None,
                        key="fecha_asig_fin"
                    )

                # Filtro Fecha Ingreso
                with fecha_cols[1]:
                    st.write("Fecha Ingreso")
                    fecha_ing_inicio = st.date_input(
                        "Desde (Ingreso)",
                        value=None,
                        key="fecha_ing_inicio"
                    )
                    fecha_ing_fin = st.date_input(
                        "Hasta (Ingreso)",
                        value=None,
                        key="fecha_ing_fin"
                    )

                # Filtro Fecha Trabajo
                with fecha_cols[2]:
                    st.write("Fecha Trabajo")
                    fecha_trab_inicio = st.date_input(
                        "Desde (Trabajo)",
                        value=None,
                        key="fecha_trab_inicio"
                    )
                    fecha_trab_fin = st.date_input(
                        "Hasta (Trabajo)",
                        value=None,
                        key="fecha_trab_fin"
                    )

                # Filtros adicionales
                st.subheader("Filtros Adicionales")
                filtros_cols = st.columns(4)  # Cambiado a 4 columnas
                
                # Filtro de Evaluador (Nuevo)
                with filtros_cols[0]:
                    evaluadores = sorted(data[COLUMNAS_FILTRO['EVALUADOR']].dropna().unique())
                    evaluadores = ['TODOS LOS EVALUADORES'] + evaluadores  # Agregar opción TODOS
                    evaluadores_seleccionados = st.multiselect(
                        "Evaluador",
                        options=evaluadores,
                        default=['TODOS LOS EVALUADORES']
                    )

                # Filtro de Proceso
                with filtros_cols[1]:
                    procesos = sorted(data[COLUMNAS_FILTRO['PROCESO']].dropna().unique())
                    procesos_seleccionados = st.multiselect(
                        "Proceso",
                        options=procesos,
                        default=[]
                    )

                # Filtro de Etapa
                with filtros_cols[2]:
                    etapas = sorted(data[COLUMNAS_FILTRO['ETAPA']].dropna().unique())
                    etapas_seleccionadas = st.multiselect(
                        "Etapa",
                        options=etapas,
                        default=[]
                    )

                # Filtro de Estado
                with filtros_cols[3]:
                    estados = sorted(data[COLUMNAS_FILTRO['ESTADO']].dropna().unique())
                    estados_seleccionados = st.multiselect(
                        "Estado",
                        options=estados,
                        default=[]
                    )

            # Botón para aplicar filtros
            col1, col2 = st.columns([1, 11])
            with col1:
                filtrar = st.button("🔍 Filtrar", key="apply_filters", type="primary")
            
            # Mostrar mensaje si no se ha filtrado
            if not filtrar:
                st.info("👆 Configura los filtros deseados y presiona el botón 'Filtrar' para ver los resultados")
                return  # Salir de la función si no se ha presionado el botón

            # Si se presionó el botón de filtrar, continuar con el procesamiento
            if filtrar:
                with st.spinner('Aplicando filtros...'):
                    # Aplicar filtros de fecha solo si se han seleccionado
                    data_filtrada = data.copy()
                    
                    if fecha_asig_inicio and fecha_asig_fin:
                        data_filtrada = data_filtrada[
                            (data_filtrada[COLUMNAS_FILTRO['FECHA_ASIGNACION']].dt.date >= fecha_asig_inicio) &
                            (data_filtrada[COLUMNAS_FILTRO['FECHA_ASIGNACION']].dt.date <= fecha_asig_fin)
                        ]
                    
                    if fecha_ing_inicio and fecha_ing_fin:
                        data_filtrada = data_filtrada[
                            (data_filtrada[COLUMNAS_FILTRO['FECHA_INGRESO']].dt.date >= fecha_ing_inicio) &
                            (data_filtrada[COLUMNAS_FILTRO['FECHA_INGRESO']].dt.date <= fecha_ing_fin)
                        ]
                    
                    if fecha_trab_inicio and fecha_trab_fin:
                        data_filtrada = data_filtrada[
                            (data_filtrada[COLUMNAS_FILTRO['FECHA_TRABAJO']].dt.date >= fecha_trab_inicio) &
                            (data_filtrada[COLUMNAS_FILTRO['FECHA_TRABAJO']].dt.date <= fecha_trab_fin)
                        ]

                    # Aplicar filtros adicionales
                    if evaluadores_seleccionados and 'TODOS LOS EVALUADORES' not in evaluadores_seleccionados:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS_FILTRO['EVALUADOR']].isin(evaluadores_seleccionados)]
                    if procesos_seleccionados:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS_FILTRO['PROCESO']].isin(procesos_seleccionados)]
                    if etapas_seleccionadas:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS_FILTRO['ETAPA']].isin(etapas_seleccionadas)]
                    if estados_seleccionados:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS_FILTRO['ESTADO']].isin(estados_seleccionados)]

                    # Crear tabla dinámica
                    if columnas_filas and columnas_columnas:
                        try:
                            pivot_table = pd.pivot_table(
                                data_filtrada,
                                values=COLUMNAS_FILTRO['EXPEDIENTE'],
                                index=[COLUMNAS_FILTRO[col] for col in columnas_filas],
                                columns=[COLUMNAS_FILTRO[col] for col in columnas_columnas],
                                aggfunc='nunique',  # Cambio a nunique para contar expedientes únicos
                                fill_value=0,
                                margins=True,
                                margins_name='Total'
                            )

                            # Mostrar resultados
                            st.subheader("Resultados del Análisis")
                            
                            # 1. Tabla Dinámica
                            st.write("Tabla Dinámica")
                            st.dataframe(pivot_table, use_container_width=True)
                            
                            # Botón para descargar tabla dinámica
                            excel_data_pivot = create_excel_download(
                                pivot_table,
                                "tabla_dinamica.xlsx",
                                "Tabla_Dinamica",
                                "Análisis Dinámico"
                            )
                            st.download_button(
                                label="📥 Descargar Tabla Dinámica",
                                data=excel_data_pivot,
                                file_name="tabla_dinamica.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                            # 2. Detalle de Expedientes
                            st.write("Detalle de Expedientes")
                            columnas_detalle = [
                                'EXPEDIENTE', 'FECHA_ASIGNACION', 'PROCESO', 'FECHA_INGRESO',
                                'EVALUADOR', 'ETAPA', 'ESTADO', 'FECHA_TRABAJO', 'BENEFICIARIO'
                            ]
                            detalle_expedientes = data_filtrada[[COLUMNAS_FILTRO[col] for col in columnas_detalle]].sort_values(
                                COLUMNAS_FILTRO['FECHA_TRABAJO']
                            )
                            st.dataframe(detalle_expedientes, use_container_width=True)

                            # Botón para descargar detalle
                            excel_data_detalle = create_excel_download(
                                detalle_expedientes,
                                "detalle_expedientes.xlsx",
                                "Detalle_Expedientes",
                                "Detalle de Expedientes Filtrados"
                            )
                            st.download_button(
                                label="📥 Descargar Detalle de Expedientes",
                                data=excel_data_detalle,
                                file_name="detalle_expedientes.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                            # 3. Visualización gráfica (si aplica)
                            if len(columnas_filas) == 1 and len(columnas_columnas) == 1:
                                st.write("Visualización Gráfica")
                                pivot_plot = pivot_table.drop('Total', axis=1).drop('Total')
                                
                                fig = px.bar(
                                    pivot_plot.reset_index().melt(
                                        id_vars=pivot_plot.index.name,
                                        var_name=columnas_columnas[0],
                                        value_name='Cantidad'
                                    ),
                                    x=pivot_plot.index.name,
                                    y='Cantidad',
                                    color=columnas_columnas[0],
                                    title=f"Distribución por {columnas_filas[0]} y {columnas_columnas[0]}",
                                    barmode='group'
                                )
                                st.plotly_chart(fig, use_container_width=True)

                        except Exception as e:
                            st.error(f"Error al crear la tabla dinámica: {str(e)}")
                    else:
                        st.warning("Por favor seleccione al menos una columna para filas y columnas")

    def render_predictive_analysis(self, data):
        """Renderizar análisis predictivo."""
        st.header("Predicción de Ingresos")

        # Mapeo de columnas
        COLUMNAS = {
            'EVALUADOR': 'EVALUADOR',
            'EXPEDIENTE': 'EXPEDIENTE',
            'FECHA_TRABAJO': 'Fecha_Trabajo'
        }

        # Convertir fecha de trabajo a datetime de manera más flexible
        try:
            data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
                data[COLUMNAS['FECHA_TRABAJO']], 
                format='mixed',  # Usar formato mixto para mayor flexibilidad
                dayfirst=True,   # Indicar que el día va primero
                errors='coerce'
            )
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return

        # Obtener fecha actual y fecha de inicio
        fecha_actual = pd.Timestamp.now()
        fecha_inicio = fecha_actual - pd.DateOffset(months=6)

        # Filtrar datos de los últimos 6 meses
        data_filtrada = data[
            (data[COLUMNAS['FECHA_TRABAJO']] >= fecha_inicio) &
            (data[COLUMNAS['FECHA_TRABAJO']] <= fecha_actual)
        ]

        # Preparar datos para el modelo de pronóstico
        datos_diarios = data_filtrada.groupby(COLUMNAS['FECHA_TRABAJO']).size().reset_index(name='cantidad')
        datos_diarios = datos_diarios.sort_values(COLUMNAS['FECHA_TRABAJO'])

        # Crear modelo de pronóstico
        model = Prophet()
        datos_diarios = datos_diarios.rename(columns={COLUMNAS['FECHA_TRABAJO']: 'ds', 'cantidad': 'y'})
        model.fit(datos_diarios)

        # Generar pronóstico para los próximos 30 días
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)

        # Mostrar tabla de pronósticos
        st.subheader("Pronósticos de Ingresos")
        forecast_table = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(30)
        forecast_table = forecast_table.rename(columns={'ds': 'Fecha', 'yhat': 'Pronóstico', 'yhat_lower': 'Límite Inferior', 'yhat_upper': 'Límite Superior'})
        st.dataframe(forecast_table)

        # Agregar botón de descarga formateado
        excel_data_forecast = create_excel_download(
            forecast_table,
            "pronosticos.xlsx",
            "Pronosticos",
            "Pronósticos de Ingresos"
        )
        
        st.download_button(
            label="📥 Descargar Pronósticos",
            data=excel_data_forecast,
            file_name="pronosticos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Gráfico de pronóstico
        fig_pronostico = go.Figure()
        fig_pronostico.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat'],
            mode='lines',
            name='Pronóstico'
        ))
        fig_pronostico.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat_lower'],
            mode='lines',
            name='Límite Inferior',
            line=dict(dash='dash')
        ))
        fig_pronostico.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat_upper'],
            mode='lines',
            name='Límite Superior',
            line=dict(dash='dash')
        ))
        fig_pronostico.add_trace(go.Scatter(
            x=datos_diarios['ds'],
            y=datos_diarios['y'],
            mode='markers',
            name='Datos Históricos'
        ))
        fig_pronostico.update_layout(
            title="Pronóstico de Ingresos",
            xaxis_title="Fecha",
            yaxis_title="Cantidad de Expedientes"
        )
        st.plotly_chart(fig_pronostico, use_container_width=True)

        # Mostrar componentes del pronóstico
        if 'df_components' in locals():
            st.subheader("Componentes de la Predicción")
            st.dataframe(df_components)

            # Agregar botón de descarga formateado
            excel_data_components = create_excel_download(
                df_components,
                "componentes_prediccion.xlsx",
                "Componentes",
                "Componentes de la Predicción"
            )
            
            st.download_button(
                label="📥 Descargar Componentes",
                data=excel_data_components,
                file_name="componentes_prediccion.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    def _show_pending_chart(self, pendientes):
        """Mostrar grfico de pendientes."""
        pendientes_por_evaluador = pendientes.groupby('EVALASIGN').size().reset_index(name='Cantidad')
        
        st.subheader("Distribución de Pendientes por Evaluador")
        fig = px.bar(
            pendientes_por_evaluador,
            x='EVALASIGN',
            y='Cantidad',
            title="Pendientes por Evaluador",
            labels={'EVALASIGN': 'Evaluador', 'Cantidad': 'Número de Expedientes'},
            text='Cantidad'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Agregar botón de descarga formateado
        excel_data_pendientes = create_excel_download(
            pendientes_por_evaluador,
            "pendientes_por_evaluador.xlsx",
            "Pendientes_Evaluador",
            "Pendientes por Evaluador"
        )
        
        st.download_button(
            label="📥 Descargar Pendientes por Evaluador",
            data=excel_data_pendientes,
            file_name="pendientes_por_evaluador.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )