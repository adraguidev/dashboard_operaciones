import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

def render_ranking_report_tab(data: pd.DataFrame, selected_module: str, rankings_collection):
    try:
        st.header("🏆 Ranking de Expedientes Trabajados")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Obtener última fecha registrada en MongoDB
        ultima_fecha_registrada = get_last_date_from_db(selected_module, rankings_collection)
        
        if ultima_fecha_registrada:
            st.info(f"📅 Último registro guardado: {ultima_fecha_registrada.strftime('%d/%m/%Y')}")
        
        # Preparar datos actuales
        data['FECHA DE TRABAJO'] = pd.to_datetime(data['FECHA DE TRABAJO'], errors='coerce')
        fecha_actual = datetime.now().date()
        fecha_ayer = fecha_actual - timedelta(days=1)
        fecha_inicio = fecha_ayer - timedelta(days=14)  # Para obtener 15 días en total
        
        # Obtener datos históricos de expedientes_db.rankings
        datos_historicos = get_rankings_from_db(
            selected_module, 
            rankings_collection, 
            fecha_inicio
        )
        
        # Preparar datos nuevos de migraciones_db
        datos_nuevos = data[
            (data['FECHA DE TRABAJO'].dt.date >= fecha_inicio) &
            (data['FECHA DE TRABAJO'].dt.date <= fecha_ayer)
        ].copy()

        # Si hay datos en ambas fuentes, combinarlos evitando duplicados
        if not datos_historicos.empty:
            # Convertir datos_nuevos al mismo formato que datos_historicos
            if not datos_nuevos.empty:
                datos_nuevos_fmt = datos_nuevos.groupby(
                    ['FECHA DE TRABAJO', 'EVALASIGN']
                ).size().reset_index(name='cantidad')
                datos_nuevos_fmt.columns = ['fecha', 'evaluador', 'cantidad']
                datos_nuevos_fmt['fecha'] = datos_nuevos_fmt['fecha'].dt.date
                
                # Eliminar fechas que ya están en datos_historicos
                fechas_historicas = set(datos_historicos['fecha'])
                datos_nuevos_fmt = datos_nuevos_fmt[
                    ~datos_nuevos_fmt['fecha'].isin(fechas_historicas)
                ]
                
                # Combinar datos
                datos_combinados = pd.concat([datos_historicos, datos_nuevos_fmt])
            else:
                datos_combinados = datos_historicos
        else:
            # Si no hay datos históricos, usar solo los nuevos
            if not datos_nuevos.empty:
                datos_combinados = datos_nuevos.groupby(
                    ['FECHA DE TRABAJO', 'EVALASIGN']
                ).size().reset_index(name='cantidad')
                datos_combinados.columns = ['fecha', 'evaluador', 'cantidad']
                datos_combinados['fecha'] = datos_combinados['fecha'].dt.date
            else:
                datos_combinados = pd.DataFrame()

        # Crear matriz de ranking
        if not datos_combinados.empty:
            matriz_ranking = pd.pivot_table(
                datos_combinados,
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
            
            # Ordenar por total descendente
            matriz_ranking = matriz_ranking.sort_values('Total', ascending=False)
            
            # Convertir todos los valores a enteros
            matriz_ranking = matriz_ranking.astype(int)

            # Formatear nombres de columnas (fechas) a dd/mm
            columnas_formateadas = {
                col: col.strftime('%d/%m') if isinstance(col, (datetime, pd.Timestamp)) else col 
                for col in matriz_ranking.columns if col != 'Total'
            }
            matriz_ranking = matriz_ranking.rename(columns=columnas_formateadas)

            # Resetear el índice para mostrar el nombre del evaluador como columna
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
                    # Preparar datos nuevos para guardar
                    fechas_disponibles = sorted(
                        datos_nuevos['FECHA DE TRABAJO'].dt.date.unique()
                    )
                    fechas_disponibles = [f for f in fechas_disponibles if f > (ultima_fecha_registrada or datetime.min.date())]
                    
                    if fechas_disponibles:
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
                            
                            # Agrupar por fecha y evaluador
                            datos_agrupados = datos_a_guardar.groupby(
                                ['FECHA DE TRABAJO', 'EVALASIGN']
                            ).size().reset_index(name='cantidad')
                            
                            save_rankings_to_db(selected_module, rankings_collection, datos_agrupados)
                            st.success("✅ Datos guardados correctamente")
                            st.rerun()

    except Exception as e:
        st.error(f"Error al procesar el ranking: {str(e)}")
        print(f"Error detallado: {str(e)}")

def get_last_date_from_db(module, collection):
    """Obtener la última fecha registrada para el módulo en expedientes_db.rankings."""
    try:
        ultimo_registro = collection.find_one(
            {"modulo": module},
            sort=[("fecha", -1)]
        )
        if ultimo_registro and 'fecha' in ultimo_registro:
            # Asegurarnos de que la fecha se convierta correctamente
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
        # Convertir start_date a datetime para la consulta
        start_datetime = datetime.combine(start_date, datetime.min.time())
        
        # Obtener registros desde la fecha de inicio
        registros = collection.find({
            "modulo": module,
            "fecha": {"$gte": start_datetime}
        }).sort("fecha", 1)
        
        data_list = []
        for registro in registros:
            # Asegurarnos de que la fecha se convierta correctamente
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
        
        # Imprimir información de depuración
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
        collection.delete_one({
            "modulo": module,
            "fecha": last_date
        })
    except Exception as e:
        raise Exception(f"Error al resetear último día: {str(e)}")