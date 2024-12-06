import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

def render_evaluator_report_tab(data: pd.DataFrame, module_name: str = None):
    try:
        st.header("👨‍💼 Reporte por Evaluador")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Lógica específica para el módulo SOL
        if module_name == 'SOL':
            render_sol_report(data)
            return

        # Resto del código existente para otros módulos...
        # [código actual]

    except Exception as e:
        st.error(f"Error al procesar el reporte: {str(e)}")
        print(f"Error detallado: {str(e)}")

def render_sol_report(data: pd.DataFrame):
    """Renderiza el reporte específico para el módulo SOL."""
    try:
        # Filtros en columnas
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
            # Filtro por estado del trámite
            estados_tramite = sorted(data['EstadoTramite'].dropna().unique())
            selected_estados = st.multiselect(
                "Estado del Trámite",
                options=estados_tramite,
                help="Filtra por estado del trámite"
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
                
                # Filtro por dependencia
                dependencias = sorted(data['Dependencia'].dropna().unique())
                selected_dependencias = st.multiselect(
                    "Dependencia",
                    options=dependencias,
                    help="Filtra por dependencia"
                )
            
            with col2:
                # Rango de fechas
                fecha_inicio = st.date_input("Fecha Desde", value=None)
                fecha_fin = st.date_input("Fecha Hasta", value=None)

        # Aplicar filtros
        filtered_data = data.copy()
        
        if selected_years:
            filtered_data = filtered_data[filtered_data['Anio'].isin(selected_years)]
            
        if selected_estados:
            filtered_data = filtered_data[filtered_data['EstadoTramite'].isin(selected_estados)]
            
        if selected_etapas:
            filtered_data = filtered_data[filtered_data['UltimaEtapa'].isin(selected_etapas)]
            
        if selected_dependencias:
            filtered_data = filtered_data[filtered_data['Dependencia'].isin(selected_dependencias)]
            
        if fecha_inicio:
            filtered_data['FechaExpendiente'] = pd.to_datetime(filtered_data['FechaExpendiente'], format='%d/%m/%Y', errors='coerce')
            filtered_data = filtered_data[filtered_data['FechaExpendiente'].dt.date >= fecha_inicio]
            
        if fecha_fin:
            if 'FechaExpendiente' not in filtered_data.columns or not pd.api.types.is_datetime64_any_dtype(filtered_data['FechaExpendiente']):
                filtered_data['FechaExpendiente'] = pd.to_datetime(filtered_data['FechaExpendiente'], format='%d/%m/%Y', errors='coerce')
            filtered_data = filtered_data[filtered_data['FechaExpendiente'].dt.date <= fecha_fin]

        # Mostrar resumen
        if not filtered_data.empty:
            st.markdown("### 📊 Resumen")
            total = len(filtered_data)
            pre_concluidos = len(filtered_data[filtered_data['Pre_Concluido'] == 'SI'])
            pendientes = total - pre_concluidos
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Expedientes", f"{total:,d}")
            col2.metric("Pre Concluidos", f"{pre_concluidos:,d}")
            col3.metric("Pendientes", f"{pendientes:,d}")

            # Mostrar datos filtrados
            st.markdown("### 📋 Detalle de Expedientes")
            
            # Preparar datos para mostrar
            display_columns = [
                'NumeroTramite', 'Dependencia', 'UltimaEtapa', 
                'FechaExpendiente', 'FechaEtapaAprobacionMasivaFin',
                'EstadoTramite', 'Pre_Concluido'
            ]
            
            display_data = filtered_data[display_columns].copy()
            
            # Mostrar tabla
            st.dataframe(
                display_data,
                use_container_width=True,
                column_config={
                    'NumeroTramite': 'Expediente',
                    'Dependencia': 'Dependencia',
                    'UltimaEtapa': 'Última Etapa',
                    'FechaExpendiente': 'Fecha Ingreso',
                    'FechaEtapaAprobacionMasivaFin': 'Fecha Aprobación',
                    'EstadoTramite': 'Estado Trámite',
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
                file_name=f"reporte_sol_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("No se encontraron expedientes con los filtros seleccionados")

    except Exception as e:
        st.error(f"Error al procesar el reporte SOL: {str(e)}")
        print(f"Error detallado: {str(e)}")

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