import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

def render_assignment_report_tab(data: pd.DataFrame):
    try:
        st.header("📋 Reporte de Asignaciones")
        
        # Validar datos
        if data is None or len(data) == 0:
            st.error("No hay datos disponibles para mostrar")
            return

        # Crear una copia eficiente de los datos
        data = data.copy()

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
            # Convertir a string primero si es categórico
            if pd.api.types.is_categorical_dtype(data['EVALASIGN']):
                data['EVALASIGN'] = data['EVALASIGN'].astype(str)
            
            # Ahora podemos llenar NaN y filtrar
            data['EVALASIGN'] = data['EVALASIGN'].fillna('').astype(str)
            evaluators = sorted(data[data['EVALASIGN'].str.strip() != '']['EVALASIGN'].unique())
            evaluators = ['TODOS LOS EVALUADORES'] + list(evaluators)
        else:
            st.error("No se encontró la columna de evaluadores")
            return

        # Filtros en columnas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Selector de evaluador
            selected_evaluator = st.selectbox(
                "Seleccionar Evaluador",
                options=evaluators,
                help="Selecciona un evaluador específico o todos los evaluadores"
            )

        with col2:
            # Selector de años
            available_years = sorted(data['Anio'].unique(), reverse=True)
            selected_years = st.multiselect(
                "Seleccionar Año(s)",
                options=available_years,
                default=[max(available_years)],
                help="Selecciona uno o varios años"
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
                
                # Rango de fechas
                fecha_inicio = st.date_input(
                    "Fecha Desde", 
                    value=None,
                    key="fecha_inicio_asig"
                )
                fecha_fin = st.date_input(
                    "Fecha Hasta", 
                    value=None,
                    key="fecha_fin_asig"
                )

        # Botón de filtrado
        col1, col2 = st.columns([1, 3])
        with col1:
            filtrar = st.button("🔍 Aplicar Filtros", type="primary")

        if filtrar:
            # Aplicar filtros
            filtered_data = data.copy()
            
            # Filtro por evaluador
            if selected_evaluator != 'TODOS LOS EVALUADORES':
                filtered_data = filtered_data[filtered_data['EVALASIGN'] == selected_evaluator]
            else:
                filtered_data = filtered_data[filtered_data['EVALASIGN'].str.strip() != '']
            
            # Filtro por año
            if selected_years:
                filtered_data = filtered_data[filtered_data['Anio'].isin(selected_years)]
            
            # Filtro por estado
            if selected_estados:
                filtered_data = filtered_data[filtered_data['ESTADO'].isin(selected_estados)]
            
            # Filtro por etapa
            if selected_etapas:
                filtered_data = filtered_data[filtered_data['UltimaEtapa'].isin(selected_etapas)]
            
            # Filtro por fechas
            if fecha_inicio:
                filtered_data = filtered_data[filtered_data['FechaExpendiente'].dt.date >= fecha_inicio]
            if fecha_fin:
                filtered_data = filtered_data[filtered_data['FechaExpendiente'].dt.date <= fecha_fin]

            # Mostrar resultados si hay datos
            if not filtered_data.empty:
                st.markdown("### 📊 Resumen")
                
                # Métricas principales
                total = len(filtered_data)
                pendientes = len(filtered_data[filtered_data['Evaluado'] == 'NO'])
                evaluados = total - pendientes
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Expedientes", f"{total:,d}")
                col2.metric("Pendientes", f"{pendientes:,d}")
                col3.metric("Evaluados", f"{evaluados:,d}")

                # Mostrar datos detallados
                st.markdown("### 📋 Detalle de Expedientes")
                
                # Preparar datos para mostrar
                display_data = filtered_data.copy()
                
                # Formatear fechas
                date_columns = display_data.select_dtypes(include=['datetime64']).columns
                for col in date_columns:
                    display_data[col] = display_data[col].dt.strftime('%d/%m/%Y')
                
                # Mostrar tabla
                st.dataframe(
                    display_data,
                    use_container_width=True
                )

                # Botones de descarga
                col1, col2 = st.columns(2)
                
                with col1:
                    # Descarga normal
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        display_data.to_excel(writer, index=False, sheet_name='Reporte')
                    output.seek(0)
                    
                    filename_prefix = "reporte_asignaciones_todos" if selected_evaluator == 'TODOS LOS EVALUADORES' else f"reporte_asignaciones_{selected_evaluator.replace(' ', '_')}"
                    
                    st.download_button(
                        label="📥 Descargar Reporte",
                        data=output,
                        file_name=f"{filename_prefix}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                with col2:
                    # Descarga formateada
                    excel_data = create_excel_download(
                        display_data,
                        f"{filename_prefix}_formateado.xlsx",
                        "Reporte_Asignaciones",
                        f"Reporte de Asignaciones - {'Todos los Evaluadores' if selected_evaluator == 'TODOS LOS EVALUADORES' else selected_evaluator}"
                    )

                    st.download_button(
                        label="📥 Descargar Reporte Formateado",
                        data=excel_data,
                        file_name=f"{filename_prefix}_formateado.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.info("No se encontraron expedientes con los filtros seleccionados")

    except Exception as e:
        st.error(f"Error al procesar el reporte de asignaciones: {str(e)}")
        import traceback
        st.error(f"Error detallado: {traceback.format_exc()}")

def process_assignment_data(data):
    """Procesar datos de asignación de los últimos 15 días."""
    try:
        # Filtrar datos recientes
        last_15_days = pd.Timestamp.now() - pd.DateOffset(days=15)
        recent_data = data[data['FechaExpendiente'] >= last_15_days]

        # Agrupar y calcular métricas
        assignment_data = recent_data.groupby('FechaExpendiente').apply(
            lambda x: pd.Series({
                'TotalExpedientes': len(x),
                'CantidadAsignados': len(x[x['EVALASIGN'] != '']),
                'CantidadSinAsignar': len(x[x['EVALASIGN'] == ''])
            })
        ).reset_index()

        # Calcular porcentajes
        assignment_data['% Sin Asignar'] = assignment_data.apply(
            lambda row: f"{(row['CantidadSinAsignar'] / row['TotalExpedientes'] * 100):.2f}%" 
            if row['TotalExpedientes'] > 0 else "0.00%",
            axis=1
        )

        # Formatear fechas
        assignment_data['FechaExpendiente'] = assignment_data['FechaExpendiente'].dt.strftime('%d/%m/%Y')

        return assignment_data

    except Exception as e:
        st.error(f"Error al procesar datos de asignación: {str(e)}")
        print(f"Error detallado en process_assignment_data: {str(e)}")
        return pd.DataFrame()

def display_assignment_data(assignment_data):
    """Mostrar tabla de datos de asignación."""
    try:
        if not assignment_data.empty:
            st.dataframe(
                assignment_data[[
                    'FechaExpendiente', 'TotalExpedientes', 
                    'CantidadAsignados', 'CantidadSinAsignar', 
                    '% Sin Asignar'
                ]],
                use_container_width=True,
                column_config={
                    'FechaExpendiente': 'Fecha',
                    'TotalExpedientes': 'Total',
                    'CantidadAsignados': 'Asignados',
                    'CantidadSinAsignar': 'Sin Asignar',
                    '% Sin Asignar': 'Porcentaje Sin Asignar'
                }
            )
        else:
            st.warning("No hay datos de asignación para mostrar")

    except Exception as e:
        st.error(f"Error al mostrar datos de asignación: {str(e)}")

def display_stacked_bar_chart(assignment_data):
    """Mostrar gráfico de barras apiladas de asignaciones."""
    try:
        if not assignment_data.empty:
            fig = px.bar(
                assignment_data,
                x='FechaExpendiente',
                y=['CantidadAsignados', 'CantidadSinAsignar'],
                title="Distribución de Expedientes Asignados y Sin Asignar (Últimos 15 Días)",
                labels={
                    'value': 'Cantidad de Expedientes',
                    'FechaExpendiente': 'Fecha',
                    'variable': 'Estado'
                },
                text_auto=True,
                color_discrete_map={
                    'CantidadAsignados': '#2ecc71',  # Verde
                    'CantidadSinAsignar': '#e74c3c'  # Rojo
                }
            )

            fig.update_layout(
                barmode='stack',
                xaxis_title='Fecha',
                yaxis_title='Cantidad de Expedientes',
                legend_title='Estado',
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # Mostrar métricas resumen
            total_asignados = assignment_data['CantidadAsignados'].sum()
            total_sin_asignar = assignment_data['CantidadSinAsignar'].sum()
            total_expedientes = total_asignados + total_sin_asignar
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Expedientes", f"{total_expedientes:,d}")
            col2.metric("Total Asignados", f"{total_asignados:,d}")
            col3.metric(
                "Sin Asignar", 
                f"{total_sin_asignar:,d}",
                f"{(total_sin_asignar/total_expedientes*100):.1f}%"
            )
        else:
            st.warning("No hay datos suficientes para mostrar el gráfico")

    except Exception as e:
        st.error(f"Error al mostrar el gráfico: {str(e)}") 