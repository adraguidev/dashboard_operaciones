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
            
            # Continuar con el resto del código para mostrar la matriz...

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
            return ultimo_registro['fecha'].date() if isinstance(ultimo_registro['fecha'], datetime) else None
        return None
    except Exception as e:
        print(f"Error al obtener última fecha: {str(e)}")
        return None

def get_rankings_from_db(module, collection, start_date):
    """Obtener los rankings desde expedientes_db.rankings."""
    try:
        # Obtener registros desde la fecha de inicio
        registros = collection.find({
            "modulo": module,
            "fecha": {"$gte": start_date}
        }).sort("fecha", 1)
        
        data_list = []
        for registro in registros:
            fecha = registro['fecha'].date() if isinstance(registro['fecha'], datetime) else None
            if fecha and 'datos' in registro:
                for evaluador_data in registro['datos']:
                    data_list.append({
                        'fecha': fecha,
                        'evaluador': evaluador_data['evaluador'],
                        'cantidad': int(evaluador_data.get('cantidad', 0))
                    })
        
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