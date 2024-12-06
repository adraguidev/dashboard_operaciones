import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

def render_ranking_report_tab(data: pd.DataFrame, selected_module: str, rankings_collection):
    try:
        st.header("🏆 Ranking de Expedientes Trabajados")
        
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Obtener última fecha registrada en MongoDB
        ultima_fecha_registrada = get_last_date_from_db(selected_module, rankings_collection)
        
        if ultima_fecha_registrada:
            st.info(f"📅 Último registro guardado: {ultima_fecha_registrada.strftime('%d/%m/%Y')}")
        
        # Preparar datos actuales
        data['FECHA DE TRABAJO'] = pd.to_datetime(data['FECHA DE TRABAJO'], errors='coerce')
        # Eliminar filas con fechas nulas
        data = data.dropna(subset=['FECHA DE TRABAJO'])
        
        fecha_actual = datetime.now().date()
        fecha_ayer = fecha_actual - timedelta(days=1)
        fecha_inicio = fecha_ayer - timedelta(days=14)
        
        # Obtener solo datos históricos de la base de datos
        datos_historicos = get_rankings_from_db(
            selected_module, 
            rankings_collection, 
            fecha_inicio
        )
        
        # Preparar datos nuevos solo para mostrar en el selector de guardado
        datos_nuevos = data[
            (data['FECHA DE TRABAJO'].dt.date >= fecha_inicio) &
            (data['FECHA DE TRABAJO'].dt.date <= fecha_ayer)
        ].copy()

        # Crear matriz de ranking solo con datos históricos
        if not datos_historicos.empty:
            matriz_ranking = pd.pivot_table(
                datos_historicos,
                values='cantidad',
                index='evaluador',
                columns='fecha',
                fill_value=0
            )
            
            # Ordenar columnas por fecha
            matriz_ranking = matriz_ranking.reindex(sorted(matriz_ranking.columns), axis=1)
            
            # Mantener solo los últimos 15 días
            ultimas_columnas = sorted(matriz_ranking.columns)[-15:]
            matriz_ranking = matriz_ranking[ultimas_columnas]

            # Agregar columna de total
            matriz_ranking['Total'] = matriz_ranking.sum(axis=1)
            matriz_ranking = matriz_ranking.sort_values('Total', ascending=False)
            matriz_ranking = matriz_ranking.astype(int)

            # Formatear nombres de columnas
            columnas_formateadas = {
                col: col.strftime('%d/%m') if isinstance(col, (datetime, pd.Timestamp)) else col 
                for col in matriz_ranking.columns if col != 'Total'
            }
            matriz_ranking = matriz_ranking.rename(columns=columnas_formateadas)
            matriz_ranking = matriz_ranking.reset_index()

            # Mostrar matriz
            st.subheader("📊 Matriz de Expedientes Trabajados por Evaluador")
            st.dataframe(
                matriz_ranking,
                use_container_width=True,
                column_config={
                    "evaluador": st.column_config.TextColumn(
                        "👨‍💼 Evaluador",
                        width="large"
                    ),
                    "Total": st.column_config.NumberColumn(
                        "📊 Total",
                        help="Total de expedientes trabajados",
                        format="%d"
                    )
                },
                hide_index=True
            )

        # Opciones para guardar/resetear datos
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            if ultima_fecha_registrada:
                if st.button("🔄 Resetear último día", 
                           help="Elimina los registros del último día para poder grabarlos nuevamente"):
                    reset_last_day(selected_module, rankings_collection, ultima_fecha_registrada)
                    st.success("✅ Último día reseteado correctamente")
                    st.rerun()

        with col2:
            if not datos_nuevos.empty:
                # Mostrar fechas disponibles para guardar
                fechas_disponibles = sorted(
                    datos_nuevos['FECHA DE TRABAJO'].dt.date.unique()
                )
                fechas_disponibles = [f for f in fechas_disponibles if f > (ultima_fecha_registrada or datetime.min.date())]
                
                if fechas_disponibles:
                    st.warning("⚠️ Hay fechas pendientes por guardar")
                    selected_dates = st.multiselect(
                        "Seleccionar fechas para guardar",
                        options=fechas_disponibles,
                        default=fechas_disponibles,
                        format_func=lambda x: x.strftime('%d/%m/%Y')
                    )
                    
                    if selected_dates and st.button("💾 Guardar datos seleccionados"):
                        datos_a_guardar = datos_nuevos[
                            datos_nuevos['FECHA DE TRABAJO'].dt.date.isin(selected_dates)
                        ].copy()
                        
                        datos_agrupados = datos_a_guardar.groupby(
                            ['FECHA DE TRABAJO', 'EVALASIGN']
                        ).size().reset_index(name='cantidad')
                        
                        save_rankings_to_db(selected_module, rankings_collection, datos_agrupados)
                        st.success("✅ Datos guardados correctamente")
                        st.rerun()

        # Agregar sección de detalle por evaluador y día
        st.markdown("---")
        st.subheader("🔍 Detalle de Expedientes por Evaluador")

        if not data.empty:
            # Obtener lista de evaluadores únicos
            evaluadores = sorted(data['EVALASIGN'].unique())
            
            # Crear selectores en dos columnas
            col1, col2 = st.columns(2)
            
            with col1:
                evaluador_seleccionado = st.selectbox(
                    "👤 Seleccionar Evaluador",
                    options=evaluadores,
                    key="evaluador_detalle"
                )
            
            with col2:
                # Obtener fechas disponibles para el evaluador seleccionado
                fechas_disponibles = data[
                    (data['EVALASIGN'] == evaluador_seleccionado) &
                    (data['FECHA DE TRABAJO'].notna())  # Asegurar que la fecha no sea nula
                ]['FECHA DE TRABAJO'].dt.date.unique()
                
                # Filtrar fechas válidas
                fechas_disponibles = [f for f in fechas_disponibles if f is not None]
                fechas_disponibles = sorted(fechas_disponibles)[-15:]  # Últimos 15 días
                
                if len(fechas_disponibles) > 0:
                    fecha_seleccionada = st.selectbox(
                        "📅 Seleccionar Fecha",
                        options=fechas_disponibles,
                        format_func=lambda x: x.strftime('%d/%m/%Y'),
                        key="fecha_detalle"
                    )
                else:
                    st.warning("No hay fechas disponibles para este evaluador")
                    fecha_seleccionada = None
            
            # Mostrar detalle del día seleccionado
            if evaluador_seleccionado and fecha_seleccionada:
                expedientes = data[
                    (data['EVALASIGN'] == evaluador_seleccionado) &
                    (data['FECHA DE TRABAJO'].dt.date == fecha_seleccionada)
                ].copy()
                
                if not expedientes.empty:
                    # Mostrar cantidad de expedientes encontrados
                    st.info(f"📁 {len(expedientes)} expedientes encontrados")
                    
                    # Seleccionar y ordenar columnas relevantes
                    columnas_mostrar = [
                        'NumeroTramite', 
                        'FECHA DE TRABAJO',
                        'EVALASIGN',
                        'ESTADO',
                        'TIPO DE TRAMITE'
                    ]
                    expedientes_mostrar = expedientes[columnas_mostrar].sort_values('NumeroTramite')
                    
                    # Mostrar tabla de expedientes
                    st.dataframe(
                        expedientes_mostrar,
                        use_container_width=True,
                        column_config={
                            "NumeroTramite": st.column_config.TextColumn(
                                "N° Expediente",
                                width="medium"
                            ),
                            "FECHA DE TRABAJO": st.column_config.DateColumn(
                                "Fecha",
                                format="DD/MM/YYYY"
                            ),
                            "EVALASIGN": "Evaluador",
                            "ESTADO": "Estado",
                            "TIPO DE TRAMITE": "Tipo de Trámite"
                        },
                        hide_index=True
                    )
                    
                    # Botón para descargar
                    if st.download_button(
                        label="📥 Descargar Expedientes",
                        data=expedientes_mostrar.to_csv(index=False),
                        file_name=f'expedientes_{evaluador_seleccionado}_{fecha_seleccionada}.csv',
                        mime='text/csv'
                    ):
                        st.success("✅ Archivo descargado exitosamente")
                else:
                    st.info("No hay expedientes registrados para la fecha seleccionada")
        else:
            st.info("No hay datos disponibles para mostrar el detalle")

    except Exception as e:
        st.error(f"Error al procesar el ranking: {str(e)}")
        print(f"Error detallado: {str(e)}")

def get_last_date_from_db(module, collection):
    """Obtener la última fecha registrada para el módulo."""
    try:
        # Buscar primero con módulo específico
        ultimo_registro = collection.find_one(
            {"modulo": module},
            sort=[("fecha", -1)]
        )
        
        # Si no encuentra, buscar sin filtro de módulo
        if not ultimo_registro:
            ultimo_registro = collection.find_one(
                {},
                sort=[("fecha", -1)]
            )
        
        if ultimo_registro and 'fecha' in ultimo_registro:
            fecha = ultimo_registro['fecha']
            if isinstance(fecha, str):
                return datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S.%f%z').date()
            return fecha.date() if isinstance(fecha, datetime) else None
        return None
    except Exception as e:
        print(f"Error al obtener última fecha: {str(e)}")
        return None

def get_rankings_from_db(module, collection, start_date):
    """Obtener los rankings desde expedientes_db.rankings."""
    try:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        
        # Buscar registros con o sin módulo
        registros = collection.find({
            "$and": [
                {"fecha": {"$gte": start_datetime}},
                {"$or": [
                    {"modulo": module},
                    {"modulo": {"$exists": False}}
                ]}
            ]
        }).sort("fecha", 1)
        
        data_list = []
        for registro in registros:
            fecha = registro['fecha']
            if isinstance(fecha, str):
                fecha = datetime.strptime(fecha, '%Y-%m-%dT%H:%M:%S.%f%z')
            fecha = fecha.date() if isinstance(fecha, datetime) else None
            
            if fecha and 'datos' in registro:
                for evaluador_data in registro['datos']:
                    data_list.append({
                        'fecha': fecha,
                        'evaluador': evaluador_data['evaluador'],
                        'cantidad': int(evaluador_data.get('cantidad', 0))
                    })
        
        print(f"Módulo: {module}")
        print(f"Fecha inicio: {start_date}")
        print(f"Registros encontrados: {len(data_list)}")
        
        return pd.DataFrame(data_list)
    except Exception as e:
        print(f"Error al obtener rankings: {str(e)}")
        return pd.DataFrame()

def save_rankings_to_db(module, collection, data):
    """Guardar nuevos rankings en MongoDB."""
    try:
        # Agrupar datos por fecha
        for fecha, grupo in data.groupby('FECHA DE TRABAJO'):
            # Preparar datos en el formato correcto
            datos_evaluadores = [
                {
                    "evaluador": row['EVALASIGN'],
                    "cantidad": int(row['cantidad'])  # Asegurar que sea entero
                }
                for _, row in grupo.iterrows()
            ]
            
            # Insertar documento con el formato correcto
            documento = {
                "modulo": module,
                "fecha": fecha.to_pydatetime(),  # Convertir a datetime para MongoDB
                "datos": datos_evaluadores
            }
            collection.insert_one(documento)
    except Exception as e:
        raise Exception(f"Error al guardar rankings: {str(e)}")

def reset_last_day(module, collection, last_date):
    """Eliminar registros del último día."""
    try:
        last_datetime = datetime.combine(last_date, datetime.min.time())
        
        # Eliminar registro con o sin módulo para esa fecha
        collection.delete_many({
            "$and": [
                {"fecha": last_datetime},
                {"$or": [
                    {"modulo": module},
                    {"modulo": {"$exists": False}}
                ]}
            ]
        })
    except Exception as e:
        raise Exception(f"Error al resetear último día: {str(e)}")