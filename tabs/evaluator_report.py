import streamlit as st
import pandas as pd
from io import BytesIO
from src.utils.excel_utils import create_excel_download

def render_evaluator_report_tab(data: pd.DataFrame):
    try:
        st.header("👨‍💼 Reporte por Evaluador")
        
        # Validar datos de manera más eficiente
        if data is None or len(data) == 0:  # Usar len en lugar de .empty
            st.error("No hay datos disponibles para mostrar")
            return

        # Optimizar la carga inicial de datos
        data = data.copy()  # Crear una copia única al inicio
        
        # Convertir fechas una sola vez al inicio
        date_columns = ['FechaExpendiente', 'FechaPre', 'FechaEtapaAprobacionMasivaFin']
        for col in date_columns:
            if col in data.columns:
                try:
                    if data[col].dtype != 'datetime64[ns]':
                        data[col] = pd.to_datetime(data[col], format='%d/%m/%Y', errors='coerce')
                except Exception:
                    pass

        # Limpiar y preparar la columna EVALASIGN una sola vez
        if 'EVALASIGN' in data.columns:
            data['EVALASIGN'] = data['EVALASIGN'].fillna('').astype(str)
            evaluators = sorted(data[data['EVALASIGN'].str.strip() != '']['EVALASIGN'].unique())
            evaluators = ['TODOS LOS EVALUADORES'] + evaluators
        
        # Verificar si es módulo SOL de manera más precisa
        is_sol_module = (
            'EstadoTramite' in data.columns and 
            'Pre_Concluido' in data.columns and
            'FechaEtapaAprobacionMasivaFin' in data.columns and
            'ESTADO' not in data.columns  # Asegurarnos que es SOL y no otro módulo
        )

        if is_sol_module:
            # Filtros específicos para SOL
            col1, col2 = st.columns(2)
            
            with col1:
                # Selector de años
                available_years = sorted(data['Anio'].unique(), reverse=True)
                selected_years = st.multiselect(
                    "Seleccionar Año(s)",
                    options=available_years,
                    default=[max(available_years)],
                    help="Selecciona uno o varios años"
                )

            with col2:
                # Selector de dependencias
                dependencias = sorted(data['Dependencia'].unique())
                selected_dependencias = st.multiselect(
                    "Seleccionar Dependencia(s)",
                    options=dependencias,
                    help="Selecciona una o varias dependencias"
                )

            # Filtros adicionales expandibles
            with st.expander("📌 Filtros Adicionales"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Filtro por última etapa
                    etapas = sorted(data['UltimaEtapa'].dropna().unique())
                    selected_etapas = st.multiselect(
                        "Última Etapa",
                        options=etapas,
                        help="Filtra por última etapa del expediente"
                    )
                    
                    # Filtro por estado de trámite
                    estados = sorted(data['EstadoTramite'].dropna().unique())
                    selected_estados = st.multiselect(
                        "Estado del Trámite",
                        options=estados,
                        help="Filtra por estado del trámite"
                    )
                
                with col2:
                    # Rango de fechas
                    fecha_inicio = st.date_input(
                        "Fecha Desde", 
                        value=None,
                        key="fecha_inicio_sol"
                    )
                    fecha_fin = st.date_input(
                        "Fecha Hasta", 
                        value=None,
                        key="fecha_fin_sol"
                    )

            # Aplicar filtros para SOL
            filtered_data = data.copy()
            
            if selected_years:
                filtered_data = filtered_data[filtered_data['Anio'].isin(selected_years)]
                
            if selected_dependencias:
                filtered_data = filtered_data[filtered_data['Dependencia'].isin(selected_dependencias)]
                
            if selected_etapas:
                filtered_data = filtered_data[filtered_data['UltimaEtapa'].isin(selected_etapas)]
                
            if selected_estados:
                filtered_data = filtered_data[filtered_data['EstadoTramite'].isin(selected_estados)]
                
            if fecha_inicio:
                filtered_data = filtered_data[pd.to_datetime(filtered_data['FechaExpendiente'], format='%d/%m/%Y').dt.date >= fecha_inicio]
            if fecha_fin:
                filtered_data = filtered_data[pd.to_datetime(filtered_data['FechaExpendiente'], format='%d/%m/%Y').dt.date <= fecha_fin]

            # Mostrar resumen para SOL
            if not filtered_data.empty:
                st.markdown("### 📊 Resumen")
                total = len(filtered_data)
                aprobados = len(filtered_data[filtered_data['EstadoTramite'] == 'APROBADO'])
                pre_concluidos = len(filtered_data[filtered_data['Pre_Concluido'] == 'SI'])
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Expedientes", f"{total:,d}")
                col2.metric("Aprobados", f"{aprobados:,d}")
                col3.metric("Pre Concluidos", f"{pre_concluidos:,d}")

                # Mostrar datos filtrados
                st.markdown("### 📋 Detalle de Expedientes")
                
                # Preparar datos para mostrar
                display_data = filtered_data[[
                    'NumeroTramite', 'Dependencia', 'EstadoTramite', 
                    'UltimaEtapa', 'FechaExpendiente', 
                    'FechaEtapaAprobacionMasivaFin', 'Pre_Concluido'
                ]].copy()
                
                # Formatear fechas
                display_data['FechaExpendiente'] = pd.to_datetime(display_data['FechaExpendiente'], format='%d/%m/%Y').dt.strftime('%d/%m/%Y')
                display_data['FechaEtapaAprobacionMasivaFin'] = pd.to_datetime(display_data['FechaEtapaAprobacionMasivaFin'], format='%d/%m/%Y').dt.strftime('%d/%m/%Y')
                
                # Mostrar tabla
                st.dataframe(
                    display_data,
                    use_container_width=True,
                    column_config={
                        'NumeroTramite': 'Expediente',
                        'Dependencia': 'Dependencia',
                        'EstadoTramite': 'Estado',
                        'UltimaEtapa': 'Última Etapa',
                        'FechaExpendiente': 'Fecha Ingreso',
                        'FechaEtapaAprobacionMasivaFin': 'Fecha Aprobación',
                        'Pre_Concluido': 'Pre Concluido'
                    }
                )

                # Botón de descarga
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    display_data.to_excel(writer, index=False, sheet_name='Reporte')
                output.seek(0)
                
                st.download_button(
                    label="📥 Descargar Reporte",
                    data=output,
                    file_name=f"reporte_sol_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No se encontraron expedientes con los filtros seleccionados")

        else:
            # Asegurar que EVALASIGN existe antes de continuar
            if 'EVALASIGN' not in data.columns:
                st.error("No se encontró la columna de evaluadores")
                return

            # Modificación para incluir "TODOS LOS EVALUADORES"
            data['EVALASIGN'] = data['EVALASIGN'].fillna('')
            evaluators = sorted(data[data['EVALASIGN'] != '']['EVALASIGN'].unique())
            evaluators = ['TODOS LOS EVALUADORES'] + evaluators
            
            # Selección de evaluador
            selected_evaluator = st.selectbox(
                "Seleccionar Evaluador",
                options=evaluators,
                help="Busca y selecciona un evaluador específico o todos los evaluadores"
            )

            # Filtros en columnas
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Selector de años
                available_years = sorted(data['Anio'].unique(), reverse=True)
                selected_years = st.multiselect(
                    "Seleccionar Año(s)",
                    options=available_years,
                    default=[max(available_years)],
                    help="Selecciona uno o varios años"
                )

            with col2:
                # Filtro por estado de evaluación
                estado_eval_options = ["Todos", "Pendientes", "Evaluados"]
                estado_eval = st.radio(
                    "Estado de Evaluación",
                    options=estado_eval_options,
                    horizontal=True
                )

            with col3:
                # Filtro por estado del expediente
                estados_unicos = sorted(data['ESTADO'].dropna().unique())
                selected_estados = st.multiselect(
                    "Estado del Expediente",
                    options=estados_unicos,
                    help="Filtra por estados específicos"
                )

            # Filtros adicionales expandibles
            with st.expander("📌 Filtros Adicionales"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Filtro por última etapa
                    etapas = sorted(data['UltimaEtapa'].dropna().unique())
                    selected_etapas = st.multiselect(
                        "Última Etapa",
                        options=etapas,
                        help="Filtra por última etapa del expediente"
                    )
                    
                    # Rango de fechas (con keys únicos)
                    fecha_inicio = st.date_input(
                        "Fecha Desde", 
                        value=None,
                        key="fecha_inicio_otros"
                    )
                    fecha_fin = st.date_input(
                        "Fecha Hasta", 
                        value=None,
                        key="fecha_fin_otros"
                    )

            # Agregar botón de filtrado después de todos los filtros
            col1, col2 = st.columns([1, 3])
            with col1:
                filtrar = st.button("🔍 Aplicar Filtros", type="primary")

            @st.cache_data  # Cachear los resultados del filtrado
            def filter_data(df, evaluator, years, estados, etapas, estado_eval, fecha_inicio, fecha_fin):
                filtered = df.copy()
                
                if evaluator == 'TODOS LOS EVALUADORES':
                    filtered = filtered[filtered['EVALASIGN'].str.strip() != '']
                else:
                    filtered = filtered[filtered['EVALASIGN'] == evaluator]
                
                if years:
                    filtered = filtered[filtered['Anio'].isin(years)]
                
                if estado_eval == "Pendientes":
                    filtered = filtered[filtered['Evaluado'] == 'NO']
                elif estado_eval == "Evaluados":
                    filtered = filtered[filtered['Evaluado'] == 'SI']
                
                if selected_estados:
                    filtered = filtered[filtered['ESTADO'].isin(selected_estados)]
                
                if selected_etapas:
                    filtered = filtered[filtered['UltimaEtapa'].isin(selected_etapas)]
                
                if fecha_inicio:
                    filtered = filtered[filtered['FechaExpendiente'].dt.date >= fecha_inicio]
                if fecha_fin:
                    filtered = filtered[filtered['FechaExpendiente'].dt.date <= fecha_fin]
                
                return filtered

            # Usar la función cacheada para el filtrado
            if filtrar:
                filtered_data = filter_data(
                    data,
                    selected_evaluator,
                    selected_years,
                    selected_estados,
                    selected_etapas,
                    estado_eval,
                    fecha_inicio,
                    fecha_fin
                )
                
                # Mostrar resumen solo si hay datos filtrados
                if not filtered_data.empty:
                    st.markdown("### 📊 Resumen")
                    total = len(filtered_data)
                    pendientes = len(filtered_data[filtered_data['Evaluado'] == 'NO'])
                    evaluados = total - pendientes
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Total Expedientes", f"{total:,d}")
                    col2.metric("Pendientes", f"{pendientes:,d}")
                    col3.metric("Evaluados", f"{evaluados:,d}")

                    # Mostrar datos filtrados
                    st.markdown("### 📋 Detalle de Expedientes")
                    
                    # Usar todas las columnas disponibles
                    display_data = filtered_data.copy()
                    
                    # Formatear fechas donde sea necesario
                    date_columns = display_data.select_dtypes(include=['datetime64']).columns
                    for col in date_columns:
                        display_data[col] = display_data[col].dt.strftime('%d/%m/%Y')
                    
                    # Mostrar tabla con todas las columnas
                    st.dataframe(
                        display_data,
                        use_container_width=True
                    )

                    # Botones de descarga
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Botón de descarga normal
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            display_data.to_excel(writer, index=False, sheet_name='Reporte')
                        output.seek(0)
                        
                        filename_prefix = "reporte_todos" if selected_evaluator == 'TODOS LOS EVALUADORES' else f"reporte_{selected_evaluator.replace(' ', '_')}"
                        
                        st.download_button(
                            label="📥 Descargar Reporte",
                            data=output,
                            file_name=f"{filename_prefix}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    with col2:
                        # Botón de descarga formateado
                        excel_data_evaluador = create_excel_download(
                            display_data,
                            f"{filename_prefix}_formateado.xlsx",
                            "Reporte_Evaluador",
                            f"Reporte de {'Todos los Evaluadores' if selected_evaluator == 'TODOS LOS EVALUADORES' else selected_evaluator}"
                        )

                        st.download_button(
                            label="📥 Descargar Reporte Formateado",
                            data=excel_data_evaluador,
                            file_name=f"{filename_prefix}_formateado.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.info("No se encontraron expedientes con los filtros seleccionados")

    except Exception as e:
        st.error(f"Error al procesar el reporte: {str(e)}")
        import traceback
        st.error(f"Error detallado: {traceback.format_exc()}")

def get_evaluators_with_pendings(data):
    """Obtener lista ordenada de evaluadores con expedientes pendientes."""
    return sorted(data[data['Evaluado'] == 'NO']['EVALASIGN'].dropna().unique())

def get_selected_months(data, selected_years):
    """Obtener meses seleccionados para los años elegidos."""
    months = sorted(data[data['Anio'].isin(selected_years)]['Mes'].unique())
    month_names = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    month_options = [month_names[m] for m in months]
    month_mapping = {v: k for k, v in month_names.items()}
    
    selected_month_names = st.multiselect(
        "Selecciona uno o varios Meses", 
        options=month_options
    )
    
    return [month_mapping[m] for m in selected_month_names]

def filter_evaluator_data(data, evaluator, years, months):
    """Filtrar datos según los criterios seleccionados."""
    filtered_data = data[data['EVALASIGN'] == evaluator]

    if years:
        filtered_data = filtered_data[filtered_data['Anio'].isin(years)]

    if months:
        filtered_data = filtered_data[filtered_data['Mes'].isin(months)]

    return filtered_data[filtered_data['Evaluado'] == 'NO']

def display_filtered_results(filtered_data):
    """Mostrar resultados filtrados y opciones de descarga."""
    if not filtered_data.empty:
        st.subheader(f"Reporte de Expedientes Pendientes")
        st.dataframe(filtered_data)

        st.subheader("Descarga de Reporte")
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            filtered_data.to_excel(writer, index=False, sheet_name='Reporte')
        output.seek(0)

        st.download_button(
            label="Descargar Reporte en Excel",
            data=output,
            file_name=f"Reporte_{filtered_data['EVALASIGN'].iloc[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("No se encontraron expedientes pendientes para los filtros seleccionados.") 