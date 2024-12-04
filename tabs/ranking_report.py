import pytz
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from config.settings import MONGODB_CONFIG

def render_ranking_report_tab(data, selected_module, collection):
    st.header("Ranking de Expedientes Trabajados")

    try:
        # Configurar zona horaria de Perú
        peru_tz = pytz.timezone('America/Lima')
        now = datetime.now(peru_tz)
        
        # Obtener fecha de ayer (hora Perú)
        yesterday = pd.Timestamp(now).normalize() - pd.Timedelta(days=1)
        yesterday = yesterday.tz_localize(None)
        
        if data is None:
            st.warning(f"No se encontraron datos para el módulo {selected_module}.")
            return

        # Convertir fechas con manejo de errores
        def convert_dates(date_str):
            try:
                return pd.to_datetime(date_str, format='%d/%m/%Y', errors='coerce')
            except:
                try:
                    cleaned_date = date_str.split('_')[0] if '_' in date_str else date_str
                    return pd.to_datetime(cleaned_date, format='%d/%m/%Y', errors='coerce')
                except:
                    return pd.NaT

        # Convertir las fechas
        data['FechaPre'] = data['FechaPre'].apply(convert_dates)
        data['FECHA DE TRABAJO'] = data['FECHA DE TRABAJO'].apply(convert_dates)
        data = data.dropna(subset=['FECHA DE TRABAJO', 'FechaPre'])

        # Obtener registros históricos
        registros_historicos = list(collection.find({
            "modulo": selected_module,
            "fecha": {"$lt": pd.Timestamp(now.date(), tz='America/Lima')}
        }).sort("fecha", -1))

        # Preparar DataFrame histórico
        df_historico = pd.DataFrame()
        fechas_guardadas = set()

        # Procesar registros históricos
        if registros_historicos:
            for registro in registros_historicos:
                fecha = pd.Timestamp(registro['fecha'])
                fechas_guardadas.add(fecha.date())
                
                # Agregar día de la semana
                dia_semana = {
                    0: 'Lun', 1: 'Mar', 2: 'Mie',
                    3: 'Jue', 4: 'Vie', 5: 'Sab', 6: 'Dom'
                }[fecha.weekday()]
                
                fecha_str = f"{dia_semana} {fecha.strftime('%d/%m')}"
                df_temp = pd.DataFrame(registro['datos'])
                
                if not df_temp.empty:
                    evaluador_col = 'EVALASIGN' if 'EVALASIGN' in df_temp.columns else 'evaluador'
                    df_pivot = pd.DataFrame({
                        'EVALASIGN': df_temp[evaluador_col].tolist(),
                        fecha_str: df_temp['cantidad'].tolist()
                    })
                    if df_historico.empty:
                        df_historico = df_pivot
                    else:
                        df_historico = df_historico.merge(
                            df_pivot, on='EVALASIGN', how='outer'
                        )

        # Procesar datos del día anterior si no están guardados
        datos_ayer = None
        if yesterday.date() not in fechas_guardadas:
            datos_dia_anterior = data[data['FECHA DE TRABAJO'].dt.date == yesterday.date()]
            if not datos_dia_anterior.empty:
                datos_ayer = datos_dia_anterior.groupby('EVALASIGN').size().reset_index(name='cantidad')
                dia_semana = {
                    0: 'Lun', 1: 'Mar', 2: 'Mie',
                    3: 'Jue', 4: 'Vie', 5: 'Sab', 6: 'Dom'
                }[yesterday.weekday()]
                fecha_str = f"{dia_semana} {yesterday.strftime('%d/%m')}"
                
                df_pivot = pd.DataFrame({
                    'EVALASIGN': datos_ayer['EVALASIGN'].tolist(),
                    fecha_str: datos_ayer['cantidad'].tolist()
                })
                if df_historico.empty:
                    df_historico = df_pivot
                else:
                    df_historico = df_historico.merge(
                        df_pivot, on='EVALASIGN', how='outer'
                    )

        # Mostrar tabla de ranking
        if not df_historico.empty:
            df_historico = df_historico.fillna(0)
            
            # Ordenar columnas cronológicamente
            cols_fecha = [col for col in df_historico.columns if col != 'EVALASIGN']
            cols_ordenadas = ['EVALASIGN'] + sorted(
                cols_fecha,
                key=lambda x: pd.to_datetime(x.split(' ')[-1] + f"/{datetime.now().year}", format='%d/%m/%Y')
            )
            
            df_historico = df_historico[cols_ordenadas]
            
            # Calcular promedio especial
            def calcular_promedio_especial(row):
                fechas_columnas = [col for col in row.index if col != 'EVALASIGN' and col not in ['Total', 'Promedio']]
                dias_trabajo = []
                
                for fecha_col in fechas_columnas:
                    fecha_str = fecha_col.split(' ')[-1]
                    fecha_completa = pd.to_datetime(fecha_str + f"/{datetime.now().year}", format='%d/%m/%Y')
                    dia_semana = fecha_completa.weekday()
                    cantidad = row[fecha_col]
                    
                    if cantidad > 0:
                        dias_trabajo.append((fecha_str, dia_semana, cantidad))
                
                dias_laborables = sum(1 for _, dia, _ in dias_trabajo if dia < 5)
                total_trabajo = sum(cantidad for _, _, cantidad in dias_trabajo)
                
                if dias_laborables == 0 and dias_trabajo:
                    return total_trabajo / 5
                
                if dias_laborables > 0:
                    return total_trabajo / 5
                
                return 0

            # Calcular totales y promedios
            df_historico['Total'] = df_historico.iloc[:, 1:].sum(axis=1)
            df_historico['Promedio'] = df_historico.apply(calcular_promedio_especial, axis=1)
            
            # Ordenar por total
            df_historico = df_historico.sort_values('Total', ascending=False)
            
            # Mostrar tabla con formato
            st.subheader(f"Ranking de Expedientes Trabajados - {selected_module} (Últimos 15 días hasta ayer)")
            st.table(
                df_historico.style.format({
                    'Promedio': "{:.1f}",
                    **{col: "{:.0f}" for col in df_historico.columns if col not in ['EVALASIGN', 'Promedio']}
                })
            )

        # Mostrar botones de acción
        col1, col2 = st.columns(2)

        with col1:
            if datos_ayer is not None and yesterday.date() not in fechas_guardadas:
                if st.button(" Guardar producción"):
                    try:
                        nuevo_registro = {
                            "fecha": yesterday.strftime("%Y-%m-%d"),
                            "datos": datos_ayer.to_dict('records'),
                            "modulo": selected_module
                        }
                        collection.insert_one(nuevo_registro)
                        st.success(f"✅ Producción guardada exitosamente para la fecha: {yesterday.strftime('%d/%m/%Y')}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar los datos: {str(e)}")

        with col2:
            if yesterday.date() in fechas_guardadas:
                if st.button("🔄 Resetear último día"):
                    try:
                        collection.delete_many({
                            "fecha": yesterday.strftime("%Y-%m-%d"),
                            "modulo": selected_module
                        })
                        st.success(f"✅ Registros del {yesterday.strftime('%d/%m/%Y')} eliminados correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al resetear el último día: {str(e)}")

    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")

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