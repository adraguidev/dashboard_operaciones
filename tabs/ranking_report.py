import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import os

@st.cache_data
def load_consolidated_cached(module_name):
    """Carga datos consolidados del módulo especificado."""
    folder = f"descargas/{module_name}"
    for file in os.listdir(folder):
        if file.startswith(f"Consolidado_{module_name}_CRUZADO") and file.endswith(".xlsx"):
            file_path = os.path.join(folder, file)
            data = pd.read_excel(file_path)
            data['Anio'] = data['Anio'].astype(int)
            data['Mes'] = data['Mes'].astype(int)
            if 'FechaExpendiente' in data.columns:
                data['FechaExpendiente'] = pd.to_datetime(data['FechaExpendiente'])
            return data
    return None

def render_ranking_report_tab(data: pd.DataFrame, selected_module: str, rankings_collection):
    try:
        st.header("🏆 Ranking de Expedientes Trabajados")
        
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Ya no necesitamos procesar CCM-LEY aquí porque viene procesado
        # del DataLoader.load_module_data()

        # Obtener última fecha registrada en MongoDB
        ultima_fecha_registrada = get_last_date_from_db(selected_module, rankings_collection)
        
        if ultima_fecha_registrada:
            st.info(f"📅 Último registro guardado: {ultima_fecha_registrada.strftime('%d/%m/%Y')}")
        
        # Resto del código...

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
        st.write(f"""
        Información de conexión:
        - Base de datos: {collection.database.name}
        - Colección: {collection.name}
        - Módulo: {module}
        """)
        
        # Mostrar un ejemplo de documento para verificar estructura
        ejemplo = collection.find_one({"modulo": module})
        if ejemplo:
            st.write("Ejemplo de documento en la colección:")
            st.write({k: v for k, v in ejemplo.items() if k != '_id'})
        
        # Buscar todos los registros del módulo sin filtro de fecha inicial
        registros = collection.find({
            "modulo": module
        }).sort("fecha", 1)
        
        data_list = []
        fechas_procesadas = set()
        
        for registro in registros:
            try:
                fecha = registro.get('fecha')
                if isinstance(fecha, dict) and '$date' in fecha:
                    # Manejar formato específico de MongoDB
                    timestamp_ms = int(fecha['$date'].get('$numberLong', 0))
                    fecha = datetime.fromtimestamp(timestamp_ms / 1000)
                
                if fecha:
                    fecha_date = fecha.date() if isinstance(fecha, datetime) else fecha
                    fechas_procesadas.add(fecha_date)
                    
                    if 'datos' in registro:
                        for evaluador_data in registro['datos']:
                            cantidad = evaluador_data.get('cantidad')
                            # Manejar cantidad en formato MongoDB
                            if isinstance(cantidad, dict) and '$numberInt' in cantidad:
                                cantidad = int(cantidad['$numberInt'])
                            elif cantidad is not None:
                                cantidad = int(cantidad)
                            
                            data_list.append({
                                'fecha': fecha_date,
                                'evaluador': evaluador_data['evaluador'],
                                'cantidad': cantidad
                            })

            except Exception as e:
                st.write(f"Error procesando registro individual: {str(e)}")
                continue

        # Información de depuración
        st.write(f"Total de fechas encontradas: {len(fechas_procesadas)}")
        st.write(f"Fechas: {sorted(fechas_procesadas)}")
        st.write(f"Total de registros procesados: {len(data_list)}")

        if data_list:
            df = pd.DataFrame(data_list)
            # Ordenar por fecha
            df = df.sort_values('fecha')
            return df

        return pd.DataFrame()
        
    except Exception as e:
        st.error(f"Error al obtener rankings: {str(e)}")
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