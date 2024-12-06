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

        # Agregar procesamiento especial para CCM-LEY
        if selected_module == 'CCM-LEY':
            # Obtener datos de CCM y CCM-ESP
            ccm_data = load_consolidated_cached('CCM')
            ccm_esp_data = load_consolidated_cached('CCM-ESP')
            
            if ccm_data is not None and ccm_esp_data is not None:
                # Filtrar CCM-LEY: registros de CCM que no están en CCM-ESP
                data = ccm_data[~ccm_data['NumeroTramite'].isin(ccm_esp_data['NumeroTramite'])]
                
                # Verificar si existe la columna TipoTramite y filtrar
                if 'TipoTramite' in data.columns:
                    data = data[data['TipoTramite'] == 'LEY'].copy()
            else:
                st.error("No se pudieron cargar los datos necesarios para CCM-LEY")
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
        
        # Obtener solo datos histricos de la base de datos
        datos_historicos = get_rankings_from_db(
            selected_module, 
            rankings_collection, 
            fecha_inicio
        )
        
        # Preparar datos nuevos solo para mostrar en el selector de guardado
        datos_nuevos = data[
            (data['FECHA DE TRABAJO'].dt.date >= fecha_inicio) &
            (data['FECHA DE TRABAJO'].dt.date <= fecha_ayer) &
            (data['EVALASIGN'].notna()) &  # Filtrar registros con evaluador
            (data['EVALASIGN'] != '') &
            (data['EVALASIGN'].str.strip() != '')
        ].copy()

        # Crear matriz de ranking solo con datos históricos
        if not datos_historicos.empty:
            # Filtrar registros sin evaluador de los datos históricos
            datos_historicos = datos_historicos[
                (datos_historicos['evaluador'].notna()) &
                (datos_historicos['evaluador'] != '') &
                (datos_historicos['evaluador'].str.strip() != '')
            ]
            
            # Convertir la columna 'fecha' a datetime si no lo está ya
            datos_historicos['fecha'] = pd.to_datetime(datos_historicos['fecha'])
            
            # Crear la matriz con el formato correcto desde el inicio
            matriz_ranking = pd.pivot_table(
                datos_historicos,
                values='cantidad',
                index='evaluador',
                columns='fecha',
                fill_value=0
            ).reset_index()
            
            # Renombrar la columna del índice
            matriz_ranking = matriz_ranking.rename(columns={'evaluador': 'Evaluador'})
            
            # Ordenar las columnas de fecha
            columnas_fecha = [col for col in matriz_ranking.columns if col != 'Evaluador']
            
            # Asegurar que tengamos exactamente los últimos 15 das
            fecha_fin = fecha_ayer
            fecha_inicio_15 = fecha_fin - timedelta(days=14)  # 14 días atrás para tener 15 días en total
            
            # Crear lista de todas las fechas necesarias
            todas_fechas = [fecha_inicio_15 + timedelta(days=x) for x in range(15)]
            
            # Asegurar que todas las fechas existan en la matriz
            for fecha in todas_fechas:
                if fecha not in columnas_fecha:
                    matriz_ranking[fecha] = 0
            
            # Obtener solo las columnas de los últimos 15 días
            columnas_fecha = sorted([col for col in matriz_ranking.columns 
                                   if isinstance(col, (datetime, pd.Timestamp)) and 
                                   fecha_inicio_15 <= col.date() <= fecha_fin])
            
            # Reordenar las columnas manteniendo 'Evaluador' primero
            matriz_ranking = matriz_ranking[['Evaluador'] + columnas_fecha]
            
            # Calcular el total y agregarlo como última columna
            matriz_ranking['Total'] = matriz_ranking[columnas_fecha].sum(axis=1)
            
            # Ordenar por total descendente
            matriz_ranking = matriz_ranking.sort_values('Total', ascending=False)
            
            # Convertir a enteros
            for col in matriz_ranking.columns:
                if col != 'Evaluador':
                    matriz_ranking[col] = matriz_ranking[col].astype(int)
            
            # Formatear las fechas en las columnas
            columnas_formateadas = {
                col: col.strftime('%d/%m') if isinstance(col, pd.Timestamp) else col
                for col in matriz_ranking.columns
            }
            matriz_ranking = matriz_ranking.rename(columns=columnas_formateadas)

            # Mostrar la matriz
            st.subheader("📊 Matriz de Expedientes Trabajados por Evaluador")
            st.dataframe(
                matriz_ranking.set_index('Evaluador'),  # Establecer Evaluador como índice
                use_container_width=True,
                column_config={
                    "Total": st.column_config.NumberColumn(
                        "📊 Total",
                        help="Total de expedientes trabajados",
                        format="%d"
                    ),
                    **{
                        col: st.column_config.NumberColumn(
                            col,
                            help="Expedientes trabajados",
                            format="%d",
                            width="small"
                        )
                        for col in matriz_ranking.columns
                        if col not in ["Evaluador", "Total"]
                    }
                }
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

        # Sección de edición manual
        st.markdown("---")
        st.subheader("✏️ Edición Manual de Registros")
        
        # Solo mostrar si hay datos históricos
        if not datos_historicos.empty:
            # Obtener lista de evaluadores únicos
            evaluadores_historicos = sorted(datos_historicos['evaluador'].unique())
            
            # Obtener fechas disponibles (solo las que ya están en la BD)
            fechas_historicas = sorted(datos_historicos['fecha'].unique())
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                evaluador_editar = st.selectbox(
                    "👤 Seleccionar Evaluador",
                    options=evaluadores_historicos,
                    key="evaluador_editar"
                )
            
            with col2:
                fecha_editar = st.selectbox(
                    "📅 Seleccionar Fecha",
                    options=fechas_historicas,
                    format_func=lambda x: x.strftime('%d/%m/%Y'),
                    key="fecha_editar"
                )
            
            with col3:
                # Obtener valor actual
                valor_actual = datos_historicos[
                    (datos_historicos['evaluador'] == evaluador_editar) &
                    (datos_historicos['fecha'] == fecha_editar)
                ]['cantidad'].iloc[0] if len(datos_historicos[
                    (datos_historicos['evaluador'] == evaluador_editar) &
                    (datos_historicos['fecha'] == fecha_editar)
                ]) > 0 else 0
                
                nuevo_valor = st.number_input(
                    "🔢 Nueva Cantidad",
                    min_value=0,
                    value=int(valor_actual),
                    step=1,
                    key="nuevo_valor"
                )
            
            # Botón para actualizar
            if st.button("💾 Actualizar Registro"):
                try:
                    # Convertir fecha a datetime para MongoDB
                    fecha_datetime = datetime.combine(fecha_editar, datetime.min.time())
                    
                    # Buscar el documento existente
                    documento = collection.find_one({
                        "fecha": fecha_datetime,
                        "modulo": selected_module
                    })
                    
                    if documento:
                        # Actualizar el valor específico
                        datos_actualizados = documento['datos']
                        for dato in datos_actualizados:
                            if dato['evaluador'] == evaluador_editar:
                                dato['cantidad'] = nuevo_valor
                                break
                        
                        # Actualizar documento en MongoDB
                        collection.update_one(
                            {
                                "fecha": fecha_datetime,
                                "modulo": selected_module
                            },
                            {
                                "$set": {
                                    "datos": datos_actualizados
                                }
                            }
                        )
                        
                        st.success("✅ Registro actualizado correctamente")
                        st.rerun()
                    else:
                        st.error("❌ No se encontró el registro en la base de datos")
                except Exception as e:
                    st.error(f"❌ Error al actualizar el registro: {str(e)}")
        else:
            st.info("ℹ️ No hay datos históricos disponibles para editar")

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
                    
                    # Lista completa de columnas deseadas
                    columnas_deseadas = [
                        'Dependencia',
                        'Anio',
                        'Mes',
                        'NumeroTramite',
                        'UltimaEtapa',
                        'FechaExpendiente',
                        'FechaEtapaAprobacionMasivaFin',
                        'FechaPre',
                        'OperadorPre',
                        'EstadoPre',
                        'EstadoTramite',
                        'Pre_Concluido',
                        'Evaluado',
                        'EVALASIGN',
                        'ESTADO',
                        'DESCRIPCION',
                        'FECHA DE TRABAJO'
                    ]
                    
                    # Filtrar solo las columnas que existen en el DataFrame
                    columnas_mostrar = [col for col in columnas_deseadas if col in expedientes.columns]
                    expedientes_mostrar = expedientes[columnas_mostrar].sort_values('NumeroTramite')
                    
                    # Convertir timestamps a fechas legibles
                    if 'FechaExpendiente' in expedientes_mostrar.columns:
                        try:
                            # Intentar primero si ya es una fecha en formato string
                            expedientes_mostrar['FechaExpendiente'] = pd.to_datetime(
                                expedientes_mostrar['FechaExpendiente'], 
                                errors='coerce',
                                format='%d/%m/%Y'
                            ).fillna(expedientes_mostrar['FechaExpendiente'])
                            
                            # Si hay valores numéricos, convertirlos desde timestamp
                            mask_numeric = expedientes_mostrar['FechaExpendiente'].astype(str).str.match(r'^\d+$')
                            if mask_numeric.any():
                                expedientes_mostrar.loc[mask_numeric, 'FechaExpendiente'] = pd.to_datetime(
                                    expedientes_mostrar.loc[mask_numeric, 'FechaExpendiente'].astype(float) / 1000,
                                    unit='s'
                                )
                            
                            # Formatear todas las fechas
                            expedientes_mostrar['FechaExpendiente'] = pd.to_datetime(
                                expedientes_mostrar['FechaExpendiente'], 
                                errors='coerce'
                            ).dt.strftime('%d/%m/%Y')
                        except Exception as e:
                            print(f"Error al convertir FechaExpendiente: {str(e)}")
                    
                    if 'FechaEtapaAprobacionMasivaFin' in expedientes_mostrar.columns:
                        try:
                            # Intentar primero si ya es una fecha en formato string
                            expedientes_mostrar['FechaEtapaAprobacionMasivaFin'] = pd.to_datetime(
                                expedientes_mostrar['FechaEtapaAprobacionMasivaFin'], 
                                errors='coerce',
                                format='%d/%m/%Y'
                            ).fillna(expedientes_mostrar['FechaEtapaAprobacionMasivaFin'])
                            
                            # Si hay valores numéricos, convertirlos desde timestamp
                            mask_numeric = expedientes_mostrar['FechaEtapaAprobacionMasivaFin'].astype(str).str.match(r'^\d+$')
                            if mask_numeric.any():
                                expedientes_mostrar.loc[mask_numeric, 'FechaEtapaAprobacionMasivaFin'] = pd.to_datetime(
                                    expedientes_mostrar.loc[mask_numeric, 'FechaEtapaAprobacionMasivaFin'].astype(float) / 1000,
                                    unit='s'
                                )
                            
                            # Formatear todas las fechas
                            expedientes_mostrar['FechaEtapaAprobacionMasivaFin'] = pd.to_datetime(
                                expedientes_mostrar['FechaEtapaAprobacionMasivaFin'], 
                                errors='coerce'
                            ).dt.strftime('%d/%m/%Y')
                        except Exception as e:
                            print(f"Error al convertir FechaEtapaAprobacionMasivaFin: {str(e)}")
                    
                    # Configuración de columnas para la visualización
                    column_config = {
                        "NumeroTramite": st.column_config.TextColumn(
                            "N° Expediente",
                            width="medium"
                        ),
                        "FECHA DE TRABAJO": st.column_config.DateColumn(
                            "Fecha de Trabajo",
                            format="DD/MM/YYYY"
                        ),
                        "FechaExpendiente": st.column_config.TextColumn(
                            "Fecha Expediente",
                            width="medium"
                        ),
                        "FechaEtapaAprobacionMasivaFin": st.column_config.TextColumn(
                            "Fecha Aprobación",
                            width="medium"
                        ),
                        "UltimaEtapa": st.column_config.TextColumn(
                            "Última Etapa",
                            width="large"
                        ),
                        "EstadoTramite": st.column_config.TextColumn(
                            "Estado Trámite",
                            width="medium"
                        ),
                        "EVALASIGN": "Evaluador",
                        "ESTADO": "Estado",
                        "Dependencia": "Dependencia",
                        "Anio": st.column_config.NumberColumn(
                            "Año",
                            format="%d"
                        ),
                        "Mes": st.column_config.NumberColumn(
                            "Mes",
                            format="%d"
                        )
                    }
                    
                    # Mostrar tabla de expedientes
                    st.dataframe(
                        expedientes_mostrar,
                        use_container_width=True,
                        column_config=column_config,
                        hide_index=True
                    )
                    
                    # Botón para descargar todos los datos
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

        # Sección de inconsistencias
        st.markdown("---")
        st.subheader("⚠ Inconsistencias Detectadas")

        # Filtrar expedientes sin evaluador
        expedientes_sin_evaluador = data[
            (data['EVALASIGN'].isna()) | 
            (data['EVALASIGN'] == '') | 
            (data['EVALASIGN'].str.strip() == '')
        ].copy()

        if not expedientes_sin_evaluador.empty:
            st.warning(f"Se encontraron {len(expedientes_sin_evaluador)} expedientes sin evaluador asignado")
            
            # Convertir timestamps a fechas legibles
            for fecha_col in ['FechaExpendiente', 'FechaEtapaAprobacionMasivaFin', 'FechaPre']:
                if fecha_col in expedientes_sin_evaluador.columns:
                    try:
                        # Convertir valores numéricos a fechas
                        mask_numeric = expedientes_sin_evaluador[fecha_col].astype(str).str.match(r'^\d+$')
                        if mask_numeric.any():
                            expedientes_sin_evaluador.loc[mask_numeric, fecha_col] = pd.to_datetime(
                                expedientes_sin_evaluador.loc[mask_numeric, fecha_col].astype(float) / 1000,
                                unit='s'
                            )
                        
                        # Convertir todas las fechas a formato dd/mm/yyyy
                        expedientes_sin_evaluador[fecha_col] = pd.to_datetime(
                            expedientes_sin_evaluador[fecha_col], 
                            errors='coerce'
                        ).dt.strftime('%d/%m/%Y')
                    except Exception as e:
                        print(f"Error al convertir {fecha_col}: {str(e)}")
            
            # Mostrar todas las columnas disponibles
            st.dataframe(
                expedientes_sin_evaluador,
                use_container_width=True,
                column_config={
                    "NumeroTramite": st.column_config.TextColumn(
                        "N° Expediente",
                        width="medium"
                    ),
                    "FECHA DE TRABAJO": st.column_config.DateColumn(
                        "Fecha de Trabajo",
                        format="DD/MM/YYYY"
                    ),
                    "FechaExpendiente": st.column_config.TextColumn(
                        "Fecha Expediente",
                        width="medium"
                    ),
                    "FechaEtapaAprobacionMasivaFin": st.column_config.TextColumn(
                        "Fecha Aprobación",
                        width="medium"
                    ),
                    "FechaPre": st.column_config.TextColumn(
                        "Fecha Pre",
                        width="medium"
                    ),
                    "EVALASIGN": "Evaluador",
                    "ESTADO": "Estado",
                    "UltimaEtapa": "Última Etapa",
                    "EstadoTramite": "Estado Trámite",
                    "EstadoPre": "Estado Pre",
                    "Pre_Concluido": "Pre Concluido",
                    "Evaluado": "Evaluado",
                    "Dependencia": "Dependencia",
                    "Anio": st.column_config.NumberColumn(
                        "Año",
                        format="%d"
                    ),
                    "Mes": st.column_config.NumberColumn(
                        "Mes",
                        format="%d"
                    ),
                    "OperadorPre": "Operador Pre",
                    "DESCRIPCION": "Descripción"
                },
                hide_index=True
            )
            
            # Botón para descargar inconsistencias
            if st.download_button(
                label="📥 Descargar Expedientes Sin Evaluador",
                data=expedientes_sin_evaluador.to_csv(index=False),
                file_name='expedientes_sin_evaluador.csv',
                mime='text/csv'
            ):
                st.success("✅ Archivo de inconsistencias descargado exitosamente")
        else:
            st.success("✅ No se encontraron expedientes sin evaluador asignado")

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
        st.write(f"Buscando registros para el módulo: {module}")
        
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