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

class SPEModule:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    def __init__(self):
        self.client = self._initialize_client()

    @staticmethod
    @st.cache_resource
    def _initialize_client():
        """Inicializar cliente de Google Sheets con caché."""
        try:
            credentials = get_google_credentials()
            return gspread.authorize(credentials)
        except Exception as e:
            st.error(f"Error al inicializar el cliente de Google Sheets: {str(e)}")
            return None

    def load_data(self):
        """Cargar datos desde Google Sheets."""
        try:
            if self.client is None:
                st.error("No se pudo inicializar el cliente de Google Sheets")
                return None
                
            sheet = self.client.open_by_key(SPE_SETTINGS['SPREADSHEET_ID']).worksheet(SPE_SETTINGS['WORKSHEET_NAME'])
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
            "Ranking de Expedientes Trabajados"
        ])
        
        with tabs[0]:
            self.render_pending_report(data)
        with tabs[1]:
            self.render_worked_report(data)
        with tabs[2]:
            self.render_ranking_report(data, collection)

    @staticmethod
    @st.cache_resource
    def _init_mongodb_connection():
        """Inicializar conexión a MongoDB."""
        return pymongo.MongoClient(st.secrets["connections"]["mongodb"]["uri"])

    def render_ranking_report(self, data, collection):
        """Renderizar pestaña de ranking de expedientes trabajados."""
        st.header("Ranking de Expedientes Trabajados")

        # Mapeo de columnas y fechas relevantes
        COLUMNAS = {
            'EVALUADOR': 'EVALUADOR',
            'EXPEDIENTE': 'EXPEDIENTE',
            'FECHA_TRABAJO': 'Fecha_Trabajo'
        }

        fecha_actual = datetime.now().date()
        fecha_ayer = fecha_actual - timedelta(days=1)

        # Convertir fecha de trabajo a datetime
        data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
            data[COLUMNAS['FECHA_TRABAJO']], 
            format='%d/%m/%Y',
            dayfirst=True,
            errors='coerce'
        )

        # Ignorar datos del día actual
        data = data[data[COLUMNAS['FECHA_TRABAJO']].dt.date < fecha_actual]

        # Obtener última fecha registrada
        ultima_fecha_db = self._get_last_date_from_db(collection)

        # Obtener datos históricos de MongoDB (EXPLÍCITAMENTE hasta ayer)
        registros_historicos = list(collection.find({
            "modulo": "SPE",
            "fecha": {"$lt": pd.Timestamp(fecha_actual)}  # Solo registros anteriores a hoy
        }).sort("fecha", -1))
        
        # Preparar DataFrame histórico desde MongoDB
        df_historico = pd.DataFrame()
        fechas_guardadas = set()
        
        # Procesar solo registros hasta ayer
        if registros_historicos:
            for registro in registros_historicos:
                fecha = pd.Timestamp(registro['fecha'])
                if fecha.date() < fecha_actual:  # Verificación adicional
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

        # Procesar datos del día anterior desde Google Sheets
        datos_ayer = None
        if fecha_ayer not in fechas_guardadas:
            # Filtrar explícitamente solo datos del día anterior
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
            
            # Filtrar explícitamente las columnas para excluir el día actual
            cols_fecha = [col for col in df_historico.columns if col != 'EVALUADOR']
            fecha_actual_str = fecha_actual.strftime('%d/%m')
            cols_fecha = [col for col in cols_fecha if col != fecha_actual_str and col != 'Total']
            
            # Ordenar columnas
            cols_ordenadas = ['EVALUADOR'] + sorted(
                cols_fecha,
                key=lambda x: pd.to_datetime(x + f"/{datetime.now().year}", format='%d/%m/%Y'),
                reverse=False
            ) + ['Total']
            
            # Usar solo las columnas que existen y no son del día actual
            cols_ordenadas = [col for col in cols_ordenadas if col in df_historico.columns and col != fecha_actual_str]
            df_historico = df_historico[cols_ordenadas]
            
            # Calcular total y ordenar
            df_historico['Total'] = df_historico.iloc[:, 1:-1].sum(axis=1)
            df_historico = df_historico.sort_values('Total', ascending=False)
            
            # Mostrar tabla
            st.dataframe(df_historico)

        # Mostrar información de última fecha y botones
        if ultima_fecha_db:
            if ultima_fecha_db.date() > fecha_ayer:
                # Eliminar automáticamente registros futuros
                collection.delete_many({
                    "modulo": "SPE",
                    "fecha": {"$gt": pd.Timestamp(fecha_ayer)}
                })
                st.warning("Se han eliminado registros futuros de la BD.")
                st.rerun()
            else:
                st.info(f"Última fecha registrada en BD: {ultima_fecha_db.strftime('%d/%m/%Y')}")
        else:
            st.warning("No hay registros en la base de datos")

        # Contenedor para los botones
        button_container = st.container()
        col1, col2 = button_container.columns(2)

        # Botón de guardar (solo para el día anterior)
        with col1:
            if datos_ayer is not None:
                if st.button("💾 Guardar producción", key="guardar_produccion"):
                    try:
                        # Si existe registro del día anterior, eliminarlo
                        if ultima_fecha_db and ultima_fecha_db.date() == fecha_ayer:
                            collection.delete_many({
                                "modulo": "SPE",
                                "fecha": ultima_fecha_db
                            })
                        
                        # Guardar nuevo registro
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

        # Botón de resetear última fecha
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
        fecha_actual = datetime.now().date()
        fecha_ayer = fecha_actual - timedelta(days=1)
        
        # Buscar el último registro que sea anterior o igual al día anterior
        ultimo_registro = collection.find_one(
            {
                "modulo": "SPE",
                "fecha": {"$lte": pd.Timestamp(fecha_ayer)}
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

        # Convertir fecha de trabajo a datetime considerando formato dd/mm/yyyy
        data[COLUMNAS['FECHA_TRABAJO']] = pd.to_datetime(
            data[COLUMNAS['FECHA_TRABAJO']], 
            format='%d/%m/%Y',
            errors='coerce'
        )

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

        # Procesar mes actual
        stats_mes_actual, nombre_mes_actual = procesar_datos_mes(fecha_actual, data)
        
        # Mostrar tabla mes actual
        st.subheader(f"Expedientes Trabajados - {nombre_mes_actual} {fecha_actual.year}")
        st.dataframe(
            stats_mes_actual,
            use_container_width=True,
            height=400
        )

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
        """Mostrar gráfico de pendientes."""
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