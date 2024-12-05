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
        
        # Filtrar datos hasta ayer
        datos_nuevos = data[data['FECHA DE TRABAJO'].dt.date <= fecha_ayer].copy()
        
        # Mostrar datos existentes vs nuevos
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Datos en Base de Datos")
            if ultima_fecha_registrada:
                datos_db = get_rankings_from_db(
                    selected_module, 
                    rankings_collection, 
                    ultima_fecha_registrada
                )
                if not datos_db.empty:
                    st.dataframe(
                        datos_db,
                        use_container_width=True,
                        column_config={
                            "fecha": "Fecha",
                            "evaluador": "Evaluador",
                            "cantidad": "Expedientes Trabajados"
                        }
                    )
                    
                    # Botón para resetear último día
                    if st.button("🔄 Resetear último día registrado", 
                               help="Elimina los registros del último día para poder grabarlos nuevamente"):
                        reset_last_day(selected_module, rankings_collection, ultima_fecha_registrada)
                        st.success("✅ Último día reseteado correctamente")
                        st.rerun()
        
        with col2:
            st.subheader("📈 Nuevos Datos Disponibles")
            # Preparar datos nuevos desde última fecha registrada
            fecha_inicio = ultima_fecha_registrada + timedelta(days=1) if ultima_fecha_registrada else None
            
            if fecha_inicio:
                datos_para_guardar = datos_nuevos[
                    (datos_nuevos['FECHA DE TRABAJO'].dt.date > ultima_fecha_registrada) &
                    (datos_nuevos['FECHA DE TRABAJO'].dt.date <= fecha_ayer)
                ]
            else:
                datos_para_guardar = datos_nuevos[
                    datos_nuevos['FECHA DE TRABAJO'].dt.date <= fecha_ayer
                ]
            
            if not datos_para_guardar.empty:
                # Agrupar por fecha y evaluador
                ranking_nuevo = datos_para_guardar.groupby(
                    [datos_para_guardar['FECHA DE TRABAJO'].dt.date, 'EVALASIGN']
                ).size().reset_index(name='cantidad')
                
                # Mostrar datos nuevos
                st.dataframe(
                    ranking_nuevo,
                    use_container_width=True,
                    column_config={
                        "FECHA DE TRABAJO": "Fecha",
                        "EVALASIGN": "Evaluador",
                        "cantidad": "Expedientes Trabajados"
                    }
                )
                
                # Botón para guardar nuevos datos
                fechas_disponibles = sorted(ranking_nuevo['FECHA DE TRABAJO'].unique())
                selected_dates = st.multiselect(
                    "Seleccionar fechas para guardar",
                    options=fechas_disponibles,
                    default=fechas_disponibles,
                    format_func=lambda x: x.strftime('%d/%m/%Y')
                )
                
                if selected_dates and st.button("💾 Guardar datos seleccionados"):
                    datos_a_guardar = ranking_nuevo[
                        ranking_nuevo['FECHA DE TRABAJO'].isin(selected_dates)
                    ]
                    save_rankings_to_db(
                        selected_module,
                        rankings_collection,
                        datos_a_guardar
                    )
                    st.success("✅ Datos guardados correctamente")
                    st.rerun()
            else:
                st.info("No hay nuevos datos para guardar")
        
        # Mostrar gráfico de tendencias
        st.subheader("📈 Tendencia de Expedientes Trabajados")
        if not datos_nuevos.empty:
            fig = px.line(
                datos_nuevos.groupby('FECHA DE TRABAJO').size().reset_index(name='cantidad'),
                x='FECHA DE TRABAJO',
                y='cantidad',
                title="Expedientes Trabajados por Día",
                labels={'FECHA DE TRABAJO': 'Fecha', 'cantidad': 'Expedientes'}
            )
            st.plotly_chart(fig, use_container_width=True)

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