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

    def render_ranking_report(self, data, collection):
        """Renderizar pestaña de ranking de expedientes trabajados."""
        st.header("Ranking de Expedientes Trabajados")

        COLUMNAS = {
            'EVALUADOR': 'EVALUADOR',
            'EXPEDIENTE': 'EXPEDIENTE',
            'FECHA_TRABAJO': 'Fecha_Trabajo'
        }

        # Usar timezone de Peru para las fechas
        fecha_actual = pd.Timestamp.now(tz='America/Lima').date()
        fecha_ayer = fecha_actual - timedelta(days=1)

        # Convertir fecha de trabajo a datetime de manera más flexible
        try:
            # Primero intentar con el formato específico
            data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
                data[COLUMNAS['FECHA_TRABAJO']], 
                format='mixed',  # Usar formato mixto para mayor flexibilidad
                dayfirst=True,   # Indicar que el día va primero
                errors='coerce'
            ).dt.tz_localize('America/Lima')
        except Exception as e:
            st.error(f"Error al procesar fechas: {str(e)}")
            return

        # Filtrar datos del día actual
        data = data[data[COLUMNAS['FECHA_TRABAJO']].dt.date < fecha_actual]

        # Obtener última fecha registrada
        ultima_fecha_db = self._get_last_date_from_db(collection)
        ultima_fecha = ultima_fecha_db.date() if ultima_fecha_db else None

        # Obtener datos históricos de MongoDB considerando timezone
        registros_historicos = list(collection.find({
            "modulo": "SPE",
            "fecha": {"$lt": pd.Timestamp(fecha_actual, tz='America/Lima')}
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

        # Procesar datos del día anterior si no están guardados
        datos_ayer = None
        if fecha_ayer not in fechas_guardadas:
            datos_dia_anterior = data[data[COLUMNAS['FECHA_TRABAJO']].dt.date == fecha_ayer]
            if not datos_dia_anterior.empty:
                datos_ayer = datos_dia_anterior.groupby(COLUMNAS['EVALUADOR']).size().reset_index(name='cantidad')
                fecha_str = fecha_ayer.strftime('%d/%m')
                df_pivot = pd.DataFrame({
                    'EVALUADOR': datos_ayer['EVALUADOR'].tolist(),
                    fecha_str: datos_ayer['cantidad'].tolist()
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

        # Mostrar información y botones
        if ultima_fecha_db:
            st.info(f"Última fecha registrada en BD: {ultima_fecha.strftime('%d/%m/%Y')}")
        else:
            st.warning("No hay registros en la base de datos")

        # Botones de acción
        col1, col2 = st.columns(2)

        with col1:
            if datos_ayer is not None and (ultima_fecha is None or ultima_fecha < fecha_ayer):
                if st.button("💾 Guardar producción", key="guardar_produccion"):
                    try:
                        nuevo_registro = {
                            "fecha": pd.Timestamp(fecha_ayer),
                            "datos": datos_ayer.to_dict('records'),
                            "modulo": "SPE"
                        }
                        collection.insert_one(nuevo_registro)
                        st.success(f"✅ Producción guardada exitosamente para la fecha: {fecha_ayer.strftime('%d/%m/%Y')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar los datos: {str(e)}")
            elif datos_ayer is not None:
                st.warning(f"Ya existe un registro para el {ultima_fecha.strftime('%d/%m/%Y')}. Use el botón de resetear si necesita modificar.")

        with col2:
            if ultima_fecha_db:
                if st.button("🔄 Resetear última fecha", key="resetear_fecha"):
                    try:
                        collection.delete_many({
                            "modulo": "SPE",
                            "fecha": ultima_fecha_db
                        })
                        st.success("✅ Última fecha eliminada correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al resetear la última fecha: {str(e)}")

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
        
        # Variación en promedio diario
        variacion_promedio = ((promedio_diario_actual / promedio_diario_anterior) - 1) * 100
        with col1:
            st.metric(
                "Variación Promedio Diario",
                f"{promedio_diario_actual:.1f}",
                f"{variacion_promedio:+.1f}%",
                help="Comparación del promedio diario actual vs mes anterior"
            )

        # Eficiencia por evaluador (días trabajados hasta la fecha)
        with col2:
            dias_habiles_anterior = stats_mes_anterior['DIAS_TRABAJADOS'].mean()
            dias_transcurridos = (fecha_actual_sin_hora - fecha_actual.replace(day=1).date()).days + 1
            dias_habiles_actual = min(dias_transcurridos, stats_mes_actual['DIAS_TRABAJADOS'].mean())
            eficiencia_dias = (dias_habiles_actual / dias_habiles_anterior) * 100
            st.metric(
                "Días Trabajados",
                f"{dias_habiles_actual:.1f} de {dias_transcurridos}",
                help="Días trabajados en el mes actual"
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

    def _show_pending_summary(self, pendientes):
        """Mostrar resumen de pendientes."""
        pendientes_por_evaluador = pendientes.groupby('EVALASIGN').size().reset_index(name='Cantidad')
        pendientes_por_evaluador = pendientes_por_evaluador.sort_values(by='Cantidad', ascending=False)

        st.subheader("Cantidad de Pendientes por Evaluador")
        st.dataframe(pendientes_por_evaluador, use_container_width=True)

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

    def _offer_pending_download(self, pendientes):
        """Ofrecer descarga de reporte de pendientes."""
        pendientes_por_evaluador = pendientes.groupby('EVALASIGN').size().reset_index(name='Cantidad')
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pendientes_por_evaluador.to_excel(writer, index=False, sheet_name='Pendientes')
            pendientes[['NumeroTramite', 'EVALASIGN', 'ETAPA_EVALUACION']].to_excel(
                writer, 
                index=False, 
                sheet_name='Detalle_Pendientes'
            )
        output.seek(0)

        st.download_button(
            label="Descargar Reporte de Pendientes",
            data=output,
            file_name="Pendientes_SPE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ) 

    def _migrate_evaluador_field(self, collection):
        """Migrar registros antiguos para usar 'EVALUADOR' en mayúsculas."""
        try:
            # Buscar registros que usan 'evaluador' en minúsculas
            registros_antiguos = collection.find({
                "modulo": "SPE",
                "datos": {"$elemMatch": {"evaluador": {"$exists": True}}}
            })
            
            for registro in registros_antiguos:
                datos_actualizados = []
                for dato in registro['datos']:
                    if 'evaluador' in dato:
                        dato['EVALUADOR'] = dato.pop('evaluador')
                    datos_actualizados.append(dato)
                
                collection.update_one(
                    {"_id": registro["_id"]},
                    {"$set": {"datos": datos_actualizados}}
                )
                
        except Exception as e:
            st.error(f"Error al migrar datos: {str(e)}") 

    def crear_filtro_fecha_jerarquico(self, df, columna_fecha):
        """Crear filtro jerárquico para fechas (Año > Mes > Día)."""
        fechas = pd.to_datetime(df[columna_fecha])
        
        # Obtener años únicos
        años = sorted(fechas.dt.year.unique())
        año_seleccionado = st.selectbox(
            f'Año ({columna_fecha})',
            options=['Todos'] + años,
            key=f'año_{columna_fecha}'
        )
        
        if año_seleccionado != 'Todos':
            # Filtrar por año
            mask_año = fechas.dt.year == año_seleccionado
            df_filtrado = df[mask_año]
            
            # Obtener meses únicos del año seleccionado
            meses = sorted(fechas[mask_año].dt.strftime('%m-%B').unique())
            mes_seleccionado = st.selectbox(
                f'Mes ({columna_fecha})',
                options=['Todos'] + meses,
                key=f'mes_{columna_fecha}'
            )
            
            if mes_seleccionado != 'Todos':
                # Filtrar por mes
                mes_num = mes_seleccionado.split('-')[0]
                mask_mes = fechas[mask_año].dt.strftime('%m') == mes_num
                df_filtrado = df_filtrado[mask_mes]
                
                # Obtener días únicos del mes seleccionado
                dias = sorted(fechas[mask_año & mask_mes].dt.strftime('%d').unique())
                dia_seleccionado = st.selectbox(
                    f'Día ({columna_fecha})',
                    options=['Todos'] + dias,
                    key=f'dia_{columna_fecha}'
                )
                
                if dia_seleccionado != 'Todos':
                    # Filtrar por día
                    mask_dia = fechas[mask_año & mask_mes].dt.strftime('%d') == dia_seleccionado
                    df_filtrado = df_filtrado[mask_dia]
        else:
            df_filtrado = df
        
        return df_filtrado

    def render_dynamic_analysis(self, data):
        """Renderizar análisis dinámico tipo tabla dinámica."""
        st.header("Análisis Dinámico")

        # Eliminar columnas que empiezan con "Column"
        data = data[[col for col in data.columns if not col.startswith('Column')]]

        # Definir las columnas disponibles para análisis
        COLUMNAS_DISPONIBLES = {
            'EVALUADOR': 'EVALUADOR',
            'EXPEDIENTE': 'EXPEDIENTE',
            'ETAPA': 'ETAPA_EVALUACIÓN',
            'ESTADO': 'ESTADO',
            'PROCESO': 'PROCESO',
            'FECHA_INGRESO': 'FECHA _ INGRESO',
            'FECHA_TRABAJO': 'Fecha_Trabajo'
        }

        # Convertir columnas de fecha a datetime
        COLUMNAS_FECHA = ['FECHA_INGRESO', 'FECHA_TRABAJO']
        for col in COLUMNAS_FECHA:
            try:
                data[COLUMNAS_DISPONIBLES[col]] = pd.to_datetime(
                    data[COLUMNAS_DISPONIBLES[col]], 
                    format='mixed',
                    dayfirst=True,
                    errors='coerce'
                )
            except Exception as e:
                st.error(f"Error al procesar fechas para columna {col}: {str(e)}")
                return

        # Mostrar gráficos de análisis
        st.subheader("Análisis General")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de expedientes por evaluador
            expedientes_por_evaluador = data.groupby(COLUMNAS_DISPONIBLES['EVALUADOR']).size().reset_index(name='cantidad')
            fig_evaluador = px.bar(
                expedientes_por_evaluador,
                x=COLUMNAS_DISPONIBLES['EVALUADOR'],
                y='cantidad',
                title='Expedientes por Evaluador',
                text_auto=True
            )
            fig_evaluador.update_traces(textposition='outside')
            st.plotly_chart(fig_evaluador, use_container_width=True)

        with col2:
            # Gráfico de expedientes por estado
            expedientes_por_estado = data.groupby(COLUMNAS_DISPONIBLES['ESTADO']).size().reset_index(name='cantidad')
            fig_estado = px.pie(
                expedientes_por_estado,
                values='cantidad',
                names=COLUMNAS_DISPONIBLES['ESTADO'],
                title='Distribución por Estado'
            )
            st.plotly_chart(fig_estado, use_container_width=True)

        # Gráfico de tendencia temporal
        expedientes_por_fecha = data.groupby(COLUMNAS_DISPONIBLES['FECHA_INGRESO']).size().reset_index(name='cantidad')
        expedientes_por_fecha = expedientes_por_fecha.sort_values(COLUMNAS_DISPONIBLES['FECHA_INGRESO'])
        
        fig_tendencia = px.line(
            expedientes_por_fecha,
            x=COLUMNAS_DISPONIBLES['FECHA_INGRESO'],
            y='cantidad',
            title='Tendencia de Expedientes a lo largo del tiempo'
        )
        st.plotly_chart(fig_tendencia, use_container_width=True)

        # Gráfico de proceso
        expedientes_por_proceso = data.groupby(COLUMNAS_DISPONIBLES['PROCESO']).size().reset_index(name='cantidad')
        fig_proceso = px.bar(
            expedientes_por_proceso,
            x=COLUMNAS_DISPONIBLES['PROCESO'],
            y='cantidad',
            title='Expedientes por Proceso',
            text_auto=True
        )
        fig_proceso.update_traces(textposition='outside')
        st.plotly_chart(fig_proceso, use_container_width=True)

        # Crear columnas adicionales para fechas (para la tabla dinámica)
        for col in COLUMNAS_FECHA:
            fecha_col = COLUMNAS_DISPONIBLES[col]
            data[f'{col}_AÑO'] = data[fecha_col].dt.year
            data[f'{col}_MES'] = data[fecha_col].dt.strftime('%B-%Y')
            data[f'{col}_DIA'] = data[fecha_col].dt.strftime('%d-%B-%Y')

        # Configuración de AgGrid
        gb = GridOptionsBuilder.from_dataframe(data)

        # Configurar columnas principales
        for col in COLUMNAS_DISPONIBLES.values():
            gb.configure_column(col, filter=True, sorteable=True)

        # Configurar columnas de fecha con filtros especiales
        for col in COLUMNAS_FECHA:
            # Ocultar columna original de fecha
            gb.configure_column(COLUMNAS_DISPONIBLES[col], hide=True)
            
            # Configurar columnas de fecha desglosadas
            gb.configure_column(
                f'{col}_AÑO',
                header_name=f'Año ({col})',
                filter='agNumberColumnFilter',
                sorteable=True
            )
            gb.configure_column(
                f'{col}_MES',
                header_name=f'Mes ({col})',
                filter='agTextColumnFilter',
                sorteable=True
            )
            gb.configure_column(
                f'{col}_DIA',
                header_name=f'Día ({col})',
                filter='agTextColumnFilter',
                sorteable=True
            )

        # Configuraciones adicionales del grid
        gb.configure_default_column(
            groupable=True,
            value=True,
            enableRowGroup=True,
            enablePivot=True,
            enableValue=True
        )
        gb.configure_side_bar()
        gb.configure_selection(selection_mode='multiple', use_checkbox=True)
        gb.configure_grid_options(
            domLayout='normal',
            enableRangeSelection=True,
            enableCharts=True
        )

        grid_options = gb.build()

        # Mostrar grid interactivo
        st.subheader("Filtrado y Análisis Avanzado")
        AgGrid(
            data,
            grid_options,
            enable_enterprise_modules=True,
            update_mode='MODEL_CHANGED',
            data_return_mode='FILTERED_AND_SORTED',
            fit_columns_on_grid_load=False,
            theme='streamlit',
            height=500,
            allow_unsafe_jscode=True
        )

    def render_predictive_analysis(self, data):
        """Renderizar análisis predictivo de ingresos usando ML y análisis estadístico avanzado."""
        st.header("Análisis Predictivo de Ingresos 2024")

        # Preparación inicial de datos
        data['FECHA _ INGRESO'] = pd.to_datetime(data['FECHA _ INGRESO'], format='%d/%m/%Y', errors='coerce')
        data = data.dropna(subset=['FECHA _ INGRESO'])
        data = data[data['FECHA _ INGRESO'].dt.year == 2024]

        # 1. Análisis Diario
        st.subheader("Evolución Diaria")
        ingresos_diarios = data.groupby('FECHA _ INGRESO').size().reset_index(name='cantidad')
        
        # Aplicar LOESS para suavizado
        x_diario = (ingresos_diarios['FECHA _ INGRESO'] - ingresos_diarios['FECHA _ INGRESO'].min()).dt.days
        tendencia_diaria = lowess(
            ingresos_diarios['cantidad'],
            x_diario,
            frac=0.3,
            it=3,
            return_sorted=False
        )

        fig_diario = go.Figure()
        fig_diario.add_trace(go.Scatter(
            x=ingresos_diarios['FECHA _ INGRESO'],
            y=ingresos_diarios['cantidad'],
            mode='markers+lines',
            name='Ingresos Diarios'
        ))
        fig_diario.add_trace(go.Scatter(
            x=ingresos_diarios['FECHA _ INGRESO'],
            y=tendencia_diaria,
            mode='lines',
            name='Tendencia'
        ))
        st.plotly_chart(fig_diario)

        # 2. Análisis con Prophet
        st.subheader("Predicción con Prophet")
        df_prophet = pd.DataFrame({
            'ds': ingresos_diarios['FECHA _ INGRESO'],
            'y': ingresos_diarios['cantidad']
        })

        model = Prophet(
            changepoint_prior_scale=0.5,
            yearly_seasonality=False,
            weekly_seasonality=True,
            daily_seasonality=False
        )
        model.fit(df_prophet)

        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)

        fig_prophet = go.Figure()
        fig_prophet.add_trace(go.Scatter(
            x=df_prophet['ds'],
            y=df_prophet['y'],
            mode='markers',
            name='Datos Históricos'
        ))
        fig_prophet.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat'],
            mode='lines',
            name='Predicción'
        ))
        fig_prophet.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat_upper'],
            fill=None,
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            name='Intervalo Superior'
        ))
        fig_prophet.add_trace(go.Scatter(
            x=forecast['ds'],
            y=forecast['yhat_lower'],
            fill='tonexty',
            mode='lines',
            line=dict(color='rgba(0,0,0,0)'),
            name='Intervalo Inferior'
        ))
        st.plotly_chart(fig_prophet)

        # 3. Análisis de Componentes
        st.subheader("Análisis de Componentes")
        fig_components = model.plot_components(forecast)
        st.pyplot(fig_components)

        # 4. Métricas y Estadísticas
        st.subheader("Métricas Clave")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            promedio = ingresos_diarios['cantidad'].mean()
            st.metric("Promedio Diario", f"{promedio:.1f}")
        
        with col2:
            tendencia = (ingresos_diarios['cantidad'].tail(7).mean() / 
                        ingresos_diarios['cantidad'].head(7).mean() - 1) * 100
            st.metric("Tendencia", f"{tendencia:.1f}%")
        
        with col3:
            volatilidad = ingresos_diarios['cantidad'].std() / promedio * 100
            st.metric("Volatilidad", f"{volatilidad:.1f}%")