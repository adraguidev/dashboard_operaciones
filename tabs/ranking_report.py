import pytz
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from config.settings import MONGODB_CONFIG

def render_ranking_report_tab(data, selected_module, collection):
    st.write("Iniciando render_ranking_report_tab")
    st.write(f"Módulo seleccionado: {selected_module}")
    
    try:
        # Verificación inicial de datos
        if data is None:
            st.warning(f"No hay datos disponibles para el módulo {selected_module}.")
            return
            
        st.write("Procesando datos...")
        
        # Convertir a DataFrame si no lo es
        if not isinstance(data, pd.DataFrame):
            st.error("Los datos no están en formato DataFrame")
            return
            
        st.write(f"Total de registros: {len(data)}")
        
        # Verificar columnas requeridas
        required_columns = ['FECHA DE TRABAJO', 'FechaPre', 'EVALASIGN']
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            st.error(f"Faltan columnas requeridas: {missing_columns}")
            return

        # Configurar zona horaria y fechas
        peru_tz = pytz.timezone('America/Lima')
        now = datetime.now(peru_tz)
        yesterday = pd.Timestamp(now).normalize() - pd.Timedelta(days=1)
        yesterday = yesterday.tz_localize(None)

        st.write("Procesando fechas...")
        
        # Convertir fechas de manera segura
        try:
            data['FECHA DE TRABAJO'] = pd.to_datetime(data['FECHA DE TRABAJO'], errors='coerce')
            data['FechaPre'] = pd.to_datetime(data['FechaPre'], errors='coerce')
        except Exception as e:
            st.error(f"Error al convertir fechas: {str(e)}")
            return

        # Verificar datos de MongoDB
        st.write("Consultando registros históricos...")
        try:
            registros_historicos = list(collection.find(
                {"modulo": selected_module},
                {"fecha": 1, "datos": 1, "_id": 0}
            ).sort("fecha", -1).limit(15))
        except Exception as e:
            st.error(f"Error al consultar MongoDB: {str(e)}")
            return

        if not registros_historicos:
            st.warning("No se encontraron registros históricos.")
            return

        st.write(f"Registros históricos encontrados: {len(registros_historicos)}")

        # Crear DataFrame histórico
        st.write("Creando DataFrame histórico...")
        try:
            df_historico = pd.DataFrame()
            for registro in registros_historicos:
                fecha = pd.Timestamp(registro['fecha']).strftime('%d/%m')
                if 'datos' not in registro or not registro['datos']:
                    continue
                    
                df_temp = pd.DataFrame(registro['datos'])
                if df_temp.empty:
                    continue
                    
                if 'evaluador' not in df_temp.columns or 'cantidad' not in df_temp.columns:
                    continue
                    
                df_pivot = pd.DataFrame({
                    'EVALASIGN': df_temp['evaluador'].tolist(),
                    fecha: df_temp['cantidad'].tolist()
                })
                
                if df_historico.empty:
                    df_historico = df_pivot
                else:
                    df_historico = df_historico.merge(df_pivot, on='EVALASIGN', how='outer')

            if df_historico.empty:
                st.warning("No se pudo crear el DataFrame histórico.")
                return

            # Llenar NaN y convertir a enteros
            df_historico = df_historico.fillna(0)
            numeric_columns = df_historico.columns.difference(['EVALASIGN'])
            df_historico[numeric_columns] = df_historico[numeric_columns].astype(int)

            # Mostrar tabla
            st.subheader(f"Ranking de Expedientes Trabajados - {selected_module}")
            st.dataframe(df_historico)

        except Exception as e:
            st.error(f"Error al procesar DataFrame histórico: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return

        # ... resto del código para inconsistencias ...

    except Exception as e:
        st.error(f"Error general: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

def get_last_date_from_db(module, collection):
    """Obtener la última fecha registrada para el módulo."""
    ultimo_registro = collection.find_one(
        {"modulo": module}, 
        sort=[("fecha", -1)]
    )
    if ultimo_registro:
        return pd.to_datetime(ultimo_registro['fecha'])
    return None

def prepare_inconsistencias_dataframe(datos_validos):
    """Prepara el DataFrame de inconsistencias para su visualización."""
    # Filtrar y crear una copia única al inicio
    mask = datos_validos['DiferenciaDias'] > 2
    columnas = ['NumeroTramite', 'EVALASIGN', 'FECHA DE TRABAJO', 'FechaPre', 'DiferenciaDias', 'ESTADO', 'DESCRIPCION']
    df = datos_validos.loc[mask, columnas].copy()
    
    if not df.empty:
        # Formatear fechas y tipos de datos
        df.loc[:, 'FECHA DE TRABAJO'] = df['FECHA DE TRABAJO'].dt.strftime('%Y-%m-%d')
        df.loc[:, 'FechaPre'] = df['FechaPre'].dt.strftime('%Y-%m-%d')
        df.loc[:, 'DiferenciaDias'] = df['DiferenciaDias'].astype(int)
        df.loc[:, 'DESCRIPCION'] = df['DESCRIPCION'].astype(str)
        
        # Renombrar columnas
        new_columns = {
            'NumeroTramite': 'N° Expediente',
            'EVALASIGN': 'Evaluador',
            'FECHA DE TRABAJO': 'Fecha de Trabajo',
            'FechaPre': 'Fecha Pre',
            'DiferenciaDias': 'Diferencia en Días',
            'ESTADO': 'Estado',
            'DESCRIPCION': 'Descripción'
        }
        df = df.rename(columns=new_columns)
        
        # Ordenar por diferencia de días
        df = df.sort_values('Diferencia en Días', ascending=False)
    
    return df 