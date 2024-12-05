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
        
        # Obtener datos históricos de los últimos 15 días
        datos_historicos = get_rankings_from_db(
            selected_module, 
            rankings_collection, 
            fecha_ayer - timedelta(days=15)
        )
        
        # Convertir datos históricos a formato de matriz
        if not datos_historicos.empty:
            matriz_historica = pd.pivot_table(
                datos_historicos,
                values='cantidad',
                index='evaluador',
                columns='fecha',
                fill_value=0
            )
        else:
            matriz_historica = pd.DataFrame()

        # Preparar datos nuevos (solo los que no están en históricos)
        if ultima_fecha_registrada:
            datos_nuevos = data[
                (data['FECHA DE TRABAJO'].dt.date > ultima_fecha_registrada) &
                (data['FECHA DE TRABAJO'].dt.date <= fecha_ayer)
            ].copy()
        else:
            datos_nuevos = data[data['FECHA DE TRABAJO'].dt.date <= fecha_ayer].copy()

        # Crear matriz de datos nuevos
        if not datos_nuevos.empty:
            matriz_nueva = pd.pivot_table(
                datos_nuevos,
                values='NumeroTramite',
                index='EVALASIGN',
                columns=datos_nuevos['FECHA DE TRABAJO'].dt.date,
                aggfunc='count',
                fill_value=0
            )
        else:
            matriz_nueva = pd.DataFrame()

        # Combinar matrices histórica y nueva
        if not matriz_historica.empty and not matriz_nueva.empty:
            matriz_ranking = pd.concat([matriz_historica, matriz_nueva], axis=1)
            # Eliminar duplicados de columnas si existen
            matriz_ranking = matriz_ranking.loc[:, ~matriz_ranking.columns.duplicated()]
        elif not matriz_historica.empty:
            matriz_ranking = matriz_historica
        else:
            matriz_ranking = matriz_nueva

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
            for col in matriz_ranking.columns
        }
        matriz_ranking = matriz_ranking.rename(columns=columnas_formateadas)

        # Mostrar matriz
        st.subheader("📊 Matriz de Expedientes Trabajados por Evaluador")
        st.dataframe(
            matriz_ranking,
            use_container_width=True,
            column_config={
                "_index": st.column_config.TextColumn("👨‍💼 Evaluador"),
                "Total": st.column_config.NumberColumn(
                    "📊 Total",
                    help="Total de expedientes trabajados",
                    format="%d"
                )
            }
        )

        # Resto del código para guardar/resetear datos...

    except Exception as e:
        st.error(f"Error al procesar el ranking: {str(e)}")
        print(f"Error detallado: {str(e)}")

def get_last_date_from_db(module, collection):
    """Obtener la última fecha registrada para el módulo."""
    try:
        ultimo_registro = collection.find_one(
            {"modulo": module},
            sort=[("fecha", -1)]
        )
        return ultimo_registro['fecha'].date() if ultimo_registro else None
    except Exception as e:
        print(f"Error al obtener última fecha: {str(e)}")
        return None

def get_rankings_from_db(module, collection, last_date):
    """Obtener los rankings desde MongoDB."""
    try:
        registros = collection.find(
            {
                "modulo": module,
                "fecha": {"$gte": last_date - timedelta(days=7)}
            }
        )
        return pd.DataFrame(list(registros))
    except Exception as e:
        print(f"Error al obtener rankings: {str(e)}")
        return pd.DataFrame()

def save_rankings_to_db(module, collection, data):
    """Guardar nuevos rankings en MongoDB."""
    try:
        records = data.to_dict('records')
        for record in records:
            collection.insert_one({
                "modulo": module,
                "fecha": record['FECHA DE TRABAJO'],
                "evaluador": record['EVALASIGN'],
                "cantidad": record['cantidad'],
                "fecha_registro": datetime.now()
            })
    except Exception as e:
        raise Exception(f"Error al guardar rankings: {str(e)}")

def reset_last_day(module, collection, last_date):
    """Eliminar registros del último día."""
    try:
        collection.delete_many({
            "modulo": module,
            "fecha": last_date
        })
    except Exception as e:
        raise Exception(f"Error al resetear último día: {str(e)}")