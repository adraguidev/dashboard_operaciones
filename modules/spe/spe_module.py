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
from typing import List, Dict

class SPEModule:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self):
        self.credentials = get_google_credentials()

    def load_data(self):
        """Cargar datos desde Google Sheets."""
        try:
            if self.credentials is None:
                st.error("No se pudo inicializar el cliente de Google Sheets")
                return None
                
            sheet = gspread.authorize(self.credentials).open_by_key(SPE_SETTINGS['SPREADSHEET_ID']).worksheet(SPE_SETTINGS['WORKSHEET_NAME'])
            return pd.DataFrame(sheet.get_all_records())
        except Exception as e:
            st.error(f"Error al cargar datos de Google Sheets: {str(e)}")
            return None

    def render_module(self):
        """Renderizar el módulo SPE."""
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

    @st.cache_data(ttl=3600)  # Cache por 1 hora
    def get_historical_records(self, collection, module: str, fecha_actual: datetime) -> List[Dict]:
        """Obtiene registros históricos con caché"""
        return list(collection.find({
            "modulo": module,
            "fecha": {"$lt": fecha_actual}
        }).sort("fecha", -1))

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

        # Convertir fecha de trabajo a datetime considerando timezone
        try:
            data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
                data[COLUMNAS['FECHA_TRABAJO']], 
                format='mixed',
                dayfirst=True,
                errors='coerce'
            )
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return

        # Obtener última fecha registrada
        ultima_fecha_db = self._get_last_date_from_db(collection)
        ultima_fecha = ultima_fecha_db.date() if ultima_fecha_db else None

        if ultima_fecha:
            st.info(f"📅 Último registro guardado: {ultima_fecha.strftime('%d/%m/%Y')}")

        # Preparar datos para guardar
        datos_nuevos = data[
            (data[COLUMNAS['FECHA_TRABAJO']].dt.date <= fecha_ayer) &
            (data[COLUMNAS['FECHA_TRABAJO']].dt.date > (ultima_fecha or datetime.min.date())) &
            (data[COLUMNAS['EVALUADOR']].notna()) &
            (data[COLUMNAS['EVALUADOR']] != '')
        ].copy()

        # Obtener datos históricos de MongoDB
        registros_historicos = self.get_historical_records(collection, "SPE", fecha_actual)

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
            st.dataframe(df_historico)

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

        # Calcular tiempos promedio por evaluador
        tiempo_promedio_real = data_filtrada.groupby(COLUMNAS['EVALUADOR']).agg({
            COLUMNAS['EXPEDIENTE']: 'count',
            COLUMNAS['FECHA_TRABAJO']: lambda x: x.dt.date.nunique()
        }).reset_index()

        tiempo_promedio_real['TIEMPO_PROMEDIO'] = (
            tiempo_promedio_real[COLUMNAS['EXPEDIENTE']] / tiempo_promedio_real[COLUMNAS['FECHA_TRABAJO']]
        ).round(1)

        tiempo_promedio_real = tiempo_promedio_real.sort_values('TIEMPO_PROMEDIO', ascending=False)

        # Mostrar tabla de tiempos promedio
        st.subheader("Tiempos Promedio por Evaluador")
        st.dataframe(tiempo_promedio_real)

        # Agregar botón de descarga formateado
        excel_data_tiempos = create_excel_download(
            tiempo_promedio_real,
            "tiempos_promedio.xlsx",
            "Tiempos_Promedio",
            f"Tiempos Promedio por Evaluador"
        )
        
        st.download_button(
            label="📥 Descargar Tiempos Promedio",
            data=excel_data_tiempos,
            file_name="tiempos_promedio.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Gráfico de distribución diaria
        datos_diarios = data_filtrada.groupby(COLUMNAS['FECHA_TRABAJO']).size().reset_index(name='cantidad')

        fig_distribucion_diaria = px.line(
            datos_diarios,
            x=COLUMNAS['FECHA_TRABAJO'],
            y='cantidad',
            title="Distribución Diaria de Expedientes",
            labels={'cantidad': 'Expedientes Trabajados'}
        )
        fig_distribucion_diaria.update_traces(mode='markers+lines')
        st.plotly_chart(fig_distribucion_diaria, use_container_width=True)

        # Agregar botón de descarga formateado
        excel_data_diarios = create_excel_download(
            datos_diarios,
            "distribucion_diaria.xlsx",
            "Distribucion_Diaria",
            "Distribución Diaria de Expedientes"
        )
        
        st.download_button(
            label="📥 Descargar Distribución Diaria",
            data=excel_data_diarios,
            file_name="distribucion_diaria.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

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