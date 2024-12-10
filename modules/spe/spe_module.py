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
from statsmodels.tsa.seasonal import seasonal_decompose

class SPEModule:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # Definir el mapeo de columnas como constante de clase
    COLUMNAS = {
        'EVALUADOR': 'EVALUADOR',
        'EXPEDIENTE': 'EXPEDIENTE',
        'ETAPA': 'ETAPA_EVALUACIÓN',
        'ESTADO': 'ESTADO',
        'FECHA_TRABAJO': 'Fecha_Trabajo',
        'FECHA_ASIGNACION': 'FECHA_ASIGNACION',
        'PROCESO': 'PROCESO',
        'BENEFICIARIO': 'NOMBRES_BENEFICIARIO'
    }

    def __init__(self):
        """Inicializar módulo SPE."""
        self.credentials = get_google_credentials()
        if 'spe_data' not in st.session_state:
            st.session_state.spe_data = None
        
        # Crear una nueva instancia del diccionario de columnas para cada objeto
        self._columnas = self.COLUMNAS.copy()
        self._columnas['FECHA_INGRESO'] = 'FECHA_INGRESO'

    @property
    def columnas(self):
        """Getter para el diccionario de columnas."""
        return self._columnas

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

        COLUMNAS = self.columnas

        # Usar timezone de Peru para las fechas
        fecha_actual = pd.Timestamp.now(tz='America/Lima')
        fecha_ayer = (fecha_actual - pd.Timedelta(days=1)).date()

        # Convertir fecha de trabajo a datetime considerando timezone
        try:
            data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
                data[COLUMNAS['FECHA_TRABAJO']], 
                format='mixed',
                dayfirst=True,
                errors='coerce'
            )
            
            # Guardar las fechas inválidas antes de eliminarlas
            fechas_invalidas = data[
                (data[COLUMNAS['FECHA_TRABAJO']].isna()) & 
                (data[COLUMNAS['FECHA_TRABAJO']].astype(str) != '')
            ]
            
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return

        # Obtener última fecha registrada
        ultima_fecha_db = self._get_last_date_from_db(collection)
        ultima_fecha = ultima_fecha_db.date() if ultima_fecha_db else None

        if ultima_fecha:
            st.info(f"📅 Último registro guardado: {ultima_fecha.strftime('%d/%m/%Y')}")

        # Preparar datos para guardar (fechas anteriores a hoy no guardadas)
        datos_por_guardar = data[
            (data[COLUMNAS['FECHA_TRABAJO']].dt.date <= fecha_ayer) &
            (data[COLUMNAS['FECHA_TRABAJO']].dt.date > (ultima_fecha or datetime.min.date())) &
            (data[COLUMNAS['EVALUADOR']].notna()) &
            (data[COLUMNAS['EVALUADOR']] != '')
        ].copy()

        # Datos del día actual
        datos_hoy = data[
            (data[COLUMNAS['FECHA_TRABAJO']].dt.date == fecha_actual.date()) &
            (data[COLUMNAS['EVALUADOR']].notna()) &
            (data[COLUMNAS['EVALUADOR']] != '')
        ].copy()

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

        # Agregar datos de hoy si existen
        if not datos_hoy.empty:
            datos_hoy_agrupados = datos_hoy.groupby(COLUMNAS['EVALUADOR']).size().reset_index(name='cantidad')
            fecha_hoy_str = fecha_actual.strftime('%d/%m')
            df_hoy = pd.DataFrame({
                'EVALUADOR': datos_hoy_agrupados[COLUMNAS['EVALUADOR']].tolist(),
                fecha_hoy_str: datos_hoy_agrupados['cantidad'].tolist()
            })
            
            if df_historico.empty:
                df_historico = df_hoy
            else:
                df_historico = df_historico.merge(df_hoy, on='EVALUADOR', how='outer')

        # Mostrar tabla de ranking
        if not df_historico.empty:
            df_historico = df_historico.fillna(0)
            
            # Ordenar columnas cronológicamente
            cols_fecha = [col for col in df_historico.columns if col != 'EVALUADOR']
            cols_ordenadas = ['EVALUADOR'] + sorted(
                cols_fecha,
                key=lambda x: pd.to_datetime(x + f"/{datetime.now().year}", format='%d/%m/%Y')
            )
            
            df_historico = df_historico[cols_ordenadas]
            df_historico['Total'] = df_historico.iloc[:, 1:].sum(axis=1)
            df_historico = df_historico.sort_values('Total', ascending=False)

            # Aplicar estilo para resaltar la columna de hoy y formatear números
            fecha_hoy_str = fecha_actual.strftime('%d/%m')
            def style_dataframe(df):
                return df.style.apply(
                    lambda col: ['background-color: #90EE90' if col.name == fecha_hoy_str else '' for _ in range(len(col))]
                ).format(
                    {col: '{:.0f}' for col in df.columns if col != 'EVALUADOR'}
                )

            st.dataframe(
                style_dataframe(df_historico),
                use_container_width=True
            )

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

            # Botón de resetear último día
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

            # Botones de acción para guardar datos
            if not datos_por_guardar.empty:
                # Mostrar fechas disponibles para guardar
                fechas_disponibles = sorted(
                    datos_por_guardar[COLUMNAS['FECHA_TRABAJO']].dt.date.unique()
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
                                datos_dia = datos_por_guardar[
                                    datos_por_guardar[COLUMNAS['FECHA_TRABAJO']].dt.date == fecha
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

        COLUMNAS = self.columnas

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
                COLUMNAS['FECHA_TRABAJO']
            ]].sort_values([COLUMNAS['EVALUADOR'], COLUMNAS['FECHA_TRABAJO']])
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

        COLUMNAS = self.columnas

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
            label=f"📥 Descargar Tabla {nombre_mes_anterior}",
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

        COLUMNAS = self.columnas

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
                    evaluadores = sorted(data[COLUMNAS['EVALUADOR']].dropna().unique())
                    evaluadores = ['TODOS LOS EVALUADORES'] + evaluadores  # Agregar opción TODOS
                    evaluadores_seleccionados = st.multiselect(
                        "Evaluador",
                        options=evaluadores,
                        default=['TODOS LOS EVALUADORES']
                    )

                # Filtro de Proceso
                with filtros_cols[1]:
                    procesos = sorted(data[COLUMNAS['PROCESO']].dropna().unique())
                    procesos_seleccionados = st.multiselect(
                        "Proceso",
                        options=procesos,
                        default=[]
                    )

                # Filtro de Etapa
                with filtros_cols[2]:
                    etapas = sorted(data[COLUMNAS['ETAPA']].dropna().unique())
                    etapas_seleccionadas = st.multiselect(
                        "Etapa",
                        options=etapas,
                        default=[]
                    )

                # Filtro de Estado
                with filtros_cols[3]:
                    estados = sorted(data[COLUMNAS['ESTADO']].dropna().unique())
                    estados_seleccionados = st.multiselect(
                        "Estado",
                        options=estados,
                        default=[]
                    )

            # Bot��n para aplicar filtros
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
                            (data_filtrada[COLUMNAS['FECHA_ASIGNACION']].dt.date >= fecha_asig_inicio) &
                            (data_filtrada[COLUMNAS['FECHA_ASIGNACION']].dt.date <= fecha_asig_fin)
                        ]
                    
                    if fecha_ing_inicio and fecha_ing_fin:
                        data_filtrada = data_filtrada[
                            (data_filtrada[COLUMNAS['FECHA_INGRESO']].dt.date >= fecha_ing_inicio) &
                            (data_filtrada[COLUMNAS['FECHA_INGRESO']].dt.date <= fecha_ing_fin)
                        ]
                    
                    if fecha_trab_inicio and fecha_trab_fin:
                        data_filtrada = data_filtrada[
                            (data_filtrada[COLUMNAS['FECHA_TRABAJO']].dt.date >= fecha_trab_inicio) &
                            (data_filtrada[COLUMNAS['FECHA_TRABAJO']].dt.date <= fecha_trab_fin)
                        ]

                    # Aplicar filtros adicionales
                    if evaluadores_seleccionados and 'TODOS LOS EVALUADORES' not in evaluadores_seleccionados:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS['EVALUADOR']].isin(evaluadores_seleccionados)]
                    if procesos_seleccionados:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS['PROCESO']].isin(procesos_seleccionados)]
                    if etapas_seleccionadas:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS['ETAPA']].isin(etapas_seleccionadas)]
                    if estados_seleccionados:
                        data_filtrada = data_filtrada[data_filtrada[COLUMNAS['ESTADO']].isin(estados_seleccionados)]

                    # Crear tabla dinámica
                    if columnas_filas and columnas_columnas:
                        try:
                            pivot_table = pd.pivot_table(
                                data_filtrada,
                                values=COLUMNAS['EXPEDIENTE'],
                                index=[COLUMNAS[col] for col in columnas_filas],
                                columns=[COLUMNAS[col] for col in columnas_columnas],
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
                            detalle_expedientes = data_filtrada[[COLUMNAS[col] for col in columnas_detalle]].sort_values(
                                COLUMNAS['FECHA_TRABAJO']
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
        st.header("Análisis de Ingresos")

        try:
            # Crear una copia del DataFrame para no modificar el original
            data_copy = data.copy()
            
            # Convertir fecha de ingreso a datetime usando la referencia de clase
            data_copy[self.columnas['FECHA_INGRESO']] = pd.to_datetime(
                data_copy[self.columnas['FECHA_INGRESO']], 
                format='mixed',
                dayfirst=True,
                errors='coerce'
            )
            
            # Usar data_copy en lugar de data para el resto del análisis
            data = data_copy

        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return

        fecha_actual = pd.Timestamp.now()

        # 1. ANÁLISIS DE ÚLTIMOS 30 DÍAS
        st.subheader("📊 Ingresos Diarios (Últimos 30 días)")
        
        fecha_30_dias = fecha_actual - pd.Timedelta(days=30)
        datos_30_dias = data[data[self.columnas['FECHA_INGRESO']] >= fecha_30_dias]
        
        ingresos_diarios = datos_30_dias.groupby(
            data[self.columnas['FECHA_INGRESO']].dt.date
        ).size().reset_index(name='cantidad')
        
        # Calcular estadísticas
        promedio_diario = ingresos_diarios['cantidad'].mean()
        mediana_diaria = ingresos_diarios['cantidad'].median()
        max_diario = ingresos_diarios['cantidad'].max()
        tendencia = np.polyfit(range(len(ingresos_diarios)), ingresos_diarios['cantidad'], 1)[0]

        # Mostrar métricas clave
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Promedio Diario", f"{promedio_diario:.1f}")
        with col2:
            st.metric("Mediana Diaria", f"{mediana_diaria:.1f}")
        with col3:
            st.metric("Máximo Diario", f"{max_diario:.0f}")
        with col4:
            tendencia_texto = "↗️ Creciente" if tendencia > 0 else "↘️ Decreciente"
            st.metric("Tendencia", tendencia_texto)

        # Gráfico de ingresos diarios con línea de tendencia
        fig_diaria = go.Figure()
        
        # Datos reales
        fig_diaria.add_trace(go.Bar(
            x=ingresos_diarios['FECHA_INGRESO'],
            y=ingresos_diarios['cantidad'],
            name='Ingresos Diarios'
        ))
        
        # Línea de tendencia
        z = np.polyfit(range(len(ingresos_diarios)), ingresos_diarios['cantidad'], 1)
        p = np.poly1d(z)
        fig_diaria.add_trace(go.Scatter(
            x=ingresos_diarios['FECHA_INGRESO'],
            y=p(range(len(ingresos_diarios))),
            name='Tendencia',
            line=dict(color='red', dash='dash')
        ))
        
        fig_diaria.update_layout(
            title="Ingresos Diarios y Tendencia",
            xaxis_title="Fecha",
            yaxis_title="Cantidad de Expedientes"
        )
        st.plotly_chart(fig_diaria, use_container_width=True)

        # 2. ANÁLISIS SEMANAL DEL ÚLTIMO AÑO
        st.subheader("📈 Análisis Semanal (Último Año)")
        
        fecha_anio = fecha_actual - pd.DateOffset(years=1)
        datos_anio = data[data[self.columnas['FECHA_INGRESO']] >= fecha_anio]
        
        # Agrupar por semana
        ingresos_semanales = datos_anio.groupby(
            [data[self.columnas['FECHA_INGRESO']].dt.isocalendar().year,
            data[self.columnas['FECHA_INGRESO']].dt.isocalendar().week]
        ).agg({
            self.columnas['EXPEDIENTE']: 'count',
            self.columnas['FECHA_INGRESO']: ['min', 'max']
        }).reset_index()

        # Calcular promedio por día hábil para cada semana
        ingresos_semanales['dias_habiles'] = ingresos_semanales[self.columnas['FECHA_INGRESO']]['max'].apply(
            lambda x: len(pd.bdate_range(
                ingresos_semanales[self.columnas['FECHA_INGRESO']]['min'].iloc[0],
                x
            ))
        )
        ingresos_semanales['promedio_diario'] = ingresos_semanales[self.columnas['EXPEDIENTE']]['count'] / ingresos_semanales['dias_habiles']

        # Mostrar estadísticas semanales
        promedio_semanal = ingresos_semanales[self.columnas['EXPEDIENTE']]['count'].mean()
        tendencia_semanal = np.polyfit(range(len(ingresos_semanales)), ingresos_semanales[self.columnas['EXPEDIENTE']]['count'], 1)[0]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Promedio Semanal", f"{promedio_semanal:.1f}")
        with col2:
            tendencia_texto = "↗️ Creciente" if tendencia_semanal > 0 else "↘️ Decreciente"
            st.metric("Tendencia Semanal", tendencia_texto)

        # 3. ANÁLISIS MENSUAL COMPARATIVO
        st.subheader("📊 Comparativa Mensual")
        
        try:
            # Crear un nuevo DataFrame para el análisis mensual
            df_mensual = datos_anio.copy()
            
            # Extraer año y mes una sola vez
            df_mensual['año'] = df_mensual[self.columnas['FECHA_INGRESO']].dt.year
            df_mensual['mes'] = df_mensual[self.columnas['FECHA_INGRESO']].dt.month
            
            # Agrupar por mes usando las columnas creadas
            ingresos_mensuales = df_mensual.groupby(['año', 'mes']).agg({
                self.columnas['EXPEDIENTE']: 'count',
                self.columnas['FECHA_INGRESO']: ['min', 'max']
            }).reset_index()

            # Calcular días transcurridos
            ingresos_mensuales['dias_transcurridos'] = ingresos_mensuales[
                (self.columnas['FECHA_INGRESO'], 'max')
            ].apply(lambda x: len(pd.bdate_range(
                ingresos_mensuales[(self.columnas['FECHA_INGRESO'], 'min')].iloc[0],
                x
            )))

            # Calcular promedio diario
            ingresos_mensuales['promedio_diario'] = (
                ingresos_mensuales[(self.columnas['EXPEDIENTE'], 'count')] / 
                ingresos_mensuales['dias_transcurridos']
            )

            # Proyección del mes actual
            mes_actual = ingresos_mensuales.iloc[-1]
            fecha_inicio_mes = mes_actual[(self.columnas['FECHA_INGRESO'], 'min')]
            fecha_fin_mes = pd.Timestamp(fecha_actual.year, fecha_actual.month + 1, 1) - pd.Timedelta(days=1)
            
            dias_habiles_mes = len(pd.bdate_range(fecha_inicio_mes, fecha_fin_mes))
            proyeccion_mes = mes_actual['promedio_diario'] * dias_habiles_mes

            # Mostrar proyección
            st.info(f"📈 Proyección para el mes actual: {proyeccion_mes:.0f} expedientes")

            # Análisis de estacionalidad
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            
            # Crear mapeo de mes a nombre
            ingresos_mensuales['mes_nombre'] = ingresos_mensuales['mes'].map(
                lambda x: meses[x-1]
            )

            # Análisis de carga por mes
            meses_carga = (ingresos_mensuales.groupby('mes_nombre')['promedio_diario']
                          .mean()
                          .sort_values())

            # Mostrar análisis de estacionalidad
            st.write("🔍 Análisis de Estacionalidad:")
            col1, col2 = st.columns(2)
            with col1:
                st.write("Meses con mayor carga:")
                for mes in meses_carga.tail(3).index:
                    st.write(f"• {mes}")
            with col2:
                st.write("Meses con menor carga:")
                for mes in meses_carga.head(3).index:
                    st.write(f"• {mes}")

        except Exception as e:
            st.error(f"Error en el análisis mensual: {str(e)}")
            return

        # 4. PREDICCIONES
        st.subheader("🔮 Predicciones")
        
        # Calcular tendencia y estacionalidad
        decomposition = seasonal_decompose(
            ingresos_mensuales['promedio_diario'],
            period=12,
            extrapolate_trend='freq'
        )
        
        # Predicción para próximo mes
        tendencia_valor = decomposition.trend.iloc[-1]
        estacionalidad = decomposition.seasonal.iloc[-1]
        prediccion_proximo_mes = (tendencia_valor + estacionalidad) * dias_habiles_mes

        st.metric(
            "Predicción próximo mes",
            f"{prediccion_proximo_mes:.0f}",
            f"{((prediccion_proximo_mes - proyeccion_mes) / proyeccion_mes * 100):.1f}%"
        )

        # Recomendaciones basadas en el análisis
        st.subheader("💡 Recomendaciones")
        
        recomendaciones = []
        if tendencia > 0:
            recomendaciones.append("• La tendencia creciente sugiere preparar recursos adicionales.")
        if max_diario > promedio_diario * 1.5:
            recomendaciones.append("• Hay picos significativos de ingresos. Considerar buffer de capacidad.")
        if tendencia_semanal < 0 and tendencia > 0:
            recomendaciones.append("• Tendencia diaria y semanal difieren. Monitorear cambios de patrón.")

        for rec in recomendaciones:
            st.write(rec)