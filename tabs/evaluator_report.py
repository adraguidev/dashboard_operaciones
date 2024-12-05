import streamlit as st
import pandas as pd
from io import BytesIO

def render_evaluator_report_tab(data: pd.DataFrame):
    try:
        st.header("👨‍💼 Reporte por Evaluador")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que EVALASIGN no tiene valores None
        data['EVALASIGN'] = data['EVALASIGN'].fillna('')
        evaluators = sorted(data[data['EVALASIGN'] != '']['EVALASIGN'].unique())

        # Panel de Filtros
        st.sidebar.subheader("🎯 Filtros de Análisis")
        
        # Selección de evaluador con búsqueda
        selected_evaluator = st.sidebar.selectbox(
            "Seleccionar Evaluador",
            options=evaluators,
            help="Busca y selecciona un evaluador específico"
        )

        # Filtros de tiempo
        st.sidebar.markdown("### 📅 Filtros Temporales")
        
        # Selector de años múltiple
        available_years = sorted(data['Anio'].unique(), reverse=True)
        selected_years = st.sidebar.multiselect(
            "Seleccionar Año(s)",
            options=available_years,
            default=[max(available_years)],
            help="Selecciona uno o varios años"
        )

        # Selector de meses si hay años seleccionados
        if selected_years:
            month_names = {
                1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
            }
            
            available_months = sorted(data[data['Anio'].isin(selected_years)]['Mes'].unique())
            month_options = [month_names[m] for m in available_months]
            selected_month_names = st.sidebar.multiselect(
                "Seleccionar Mes(es)",
                options=month_options,
                help="Selecciona uno o varios meses"
            )
            
            month_mapping = {v: k for k, v in month_names.items()}
            selected_months = [month_mapping[m] for m in selected_month_names]

        # Filtros adicionales
        st.sidebar.markdown("### 🔍 Filtros Adicionales")
        
        # Filtro por estado
        estados_unicos = sorted(data['ESTADO'].dropna().unique())
        selected_estados = st.sidebar.multiselect(
            "Estados",
            options=estados_unicos,
            help="Filtra por estados específicos"
        )

        # Filtro por última etapa en lugar de tipo de expediente
        etapas_unicas = sorted(data['UltimaEtapa'].dropna().unique())
        selected_etapas = st.sidebar.multiselect(
            "Última Etapa",
            options=etapas_unicas,
            help="Filtra por última etapa del expediente"
        )

        # Aplicar filtros
        filtered_data = data[data['EVALASIGN'] == selected_evaluator]
        
        if selected_years:
            filtered_data = filtered_data[filtered_data['Anio'].isin(selected_years)]
        
        if selected_months:
            filtered_data = filtered_data[filtered_data['Mes'].isin(selected_months)]
            
        if selected_estados:
            filtered_data = filtered_data[filtered_data['ESTADO'].isin(selected_estados)]
            
        if selected_etapas:  # Cambiado de tipos a etapas
            filtered_data = filtered_data[filtered_data['UltimaEtapa'].isin(selected_etapas)]

        # Mostrar resumen estadístico
        st.subheader("📊 Resumen Estadístico")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_asignados = len(filtered_data)
            pendientes = len(filtered_data[filtered_data['Evaluado'] == 'NO'])
            st.metric(
                "Total Expedientes",
                f"{total_asignados:,d}",
                f"{pendientes:,d} pendientes",
                help="Total de expedientes asignados y pendientes"
            )
            
        with col2:
            if not filtered_data.empty:
                tiempo_promedio = (filtered_data['FechaPre'] - filtered_data['FechaExpendiente']).dt.days.median()
                st.metric(
                    "Tiempo Promedio",
                    f"{tiempo_promedio:.1f} días",
                    help="Tiempo promedio de procesamiento"
                )
            
        with col3:
            productividad = len(filtered_data[filtered_data['Evaluado'] == 'SI']) / total_asignados * 100 if total_asignados > 0 else 0
            st.metric(
                "Productividad",
                f"{productividad:.1f}%",
                help="Porcentaje de expedientes evaluados"
            )

        # Análisis de tendencias
        st.subheader("📈 Análisis de Tendencias")
        
        # Gráfico de expedientes por mes
        monthly_data = filtered_data.groupby(['Anio', 'Mes']).size().reset_index(name='Cantidad')
        monthly_data['Fecha'] = pd.to_datetime(monthly_data[['Anio', 'Mes']].assign(Day=1))
        
        fig = px.line(
            monthly_data,
            x='Fecha',
            y='Cantidad',
            title='Tendencia de Expedientes Asignados',
            labels={'Cantidad': 'Expedientes', 'Fecha': 'Período'},
        )
        st.plotly_chart(fig, use_container_width=True)

        # Distribución por estado
        if not filtered_data.empty:
            st.subheader("🔄 Distribución por Estado")
            estado_dist = filtered_data['ESTADO'].value_counts()
            fig_pie = px.pie(
                values=estado_dist.values,
                names=estado_dist.index,
                title='Distribución por Estado'
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Tabla detallada de expedientes
        st.subheader("📋 Detalle de Expedientes")
        
        # Preparar datos para la tabla
        display_columns = [
            'NumeroTramite', 'ESTADO', 'FechaExpendiente', 
            'FechaPre', 'Evaluado', 'UltimaEtapa'  # Cambiado TipoTramite por UltimaEtapa
        ]
        
        # Verificar qué columnas están disponibles
        available_columns = [col for col in display_columns if col in filtered_data.columns]
        display_data = filtered_data[available_columns].copy()
        
        # Formatear fechas
        if 'FechaExpendiente' in display_data.columns:
            display_data['FechaExpendiente'] = display_data['FechaExpendiente'].dt.strftime('%d/%m/%Y')
        if 'FechaPre' in display_data.columns:
            display_data['FechaPre'] = display_data['FechaPre'].dt.strftime('%d/%m/%Y')
        
        # Configuración de columnas dinámica
        column_config = {
            'NumeroTramite': 'Expediente',
            'ESTADO': 'Estado',
            'FechaExpendiente': 'Fecha Ingreso',
            'FechaPre': 'Fecha Pre',
            'Evaluado': 'Evaluado',
            'UltimaEtapa': 'Última Etapa'
        }
        
        # Filtrar solo las configuraciones de columnas disponibles
        column_config = {k: v for k, v in column_config.items() if k in display_data.columns}
        
        # Mostrar tabla con formato mejorado
        st.dataframe(
            display_data,
            use_container_width=True,
            column_config=column_config
        )

        # Opción de descarga
        if not display_data.empty:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                display_data.to_excel(writer, index=False, sheet_name='Reporte')
            output.seek(0)
            
            st.download_button(
                label="📥 Descargar Reporte Detallado",
                data=output,
                file_name=f"reporte_{selected_evaluator.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error al procesar el reporte: {str(e)}")
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