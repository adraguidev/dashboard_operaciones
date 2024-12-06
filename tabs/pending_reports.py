import streamlit as st
import pandas as pd
import plotly.express as px
from config.settings import INACTIVE_EVALUATORS, VULNERABILIDAD_EVALUATORS

def render_pending_reports_tab(data: pd.DataFrame, selected_module: str):
    st.header("Reporte de Pendientes")

    # Validar que tenemos datos
    if data is None or data.empty:
        st.error("No hay datos disponibles para mostrar")
        return

    # Filtros superiores
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Selector de vista
        view_type = st.radio(
            "Seleccionar Vista",
            ["Activos", "Inactivos", "Vulnerabilidad", "Total"],
            horizontal=True
        )
    
    with col2:
        # Selector de años múltiple
        try:
            available_years = sorted([
                int(year) 
                for year in data['Anio'].unique() 
                if year is not None and pd.notna(year)
            ], reverse=True)
            
            if not available_years:
                st.error("No se encontraron años válidos en los datos")
                return
                
            selected_years = st.multiselect(
                "Seleccionar Año(s)",
                options=available_years,
                default=[max(available_years)]
            )
        except Exception as e:
            st.error(f"Error al procesar los años: {str(e)}")
            return
    
    if not selected_years:
        st.warning("Por favor seleccione al menos un año")
        return

    try:
        # Filtrar datos por años seleccionados y pendientes
        filtered_data = data[
            (data['Anio'].isin(selected_years)) &
            (data['Evaluado'] == 'NO')
        ].copy()

        # Aplicar filtros según la vista seleccionada
        if view_type == "Activos":
            filtered_data = filtered_data[
                (~filtered_data['EVALASIGN'].isin(INACTIVE_EVALUATORS.get(selected_module, []))) &
                (~filtered_data['EVALASIGN'].isin(VULNERABILIDAD_EVALUATORS.get(selected_module, []))) &
                (filtered_data['EVALASIGN'].notna()) &
                (filtered_data['EVALASIGN'] != '') &
                (filtered_data['EVALASIGN'] != 'SUSPENDIDA')
            ]
        elif view_type == "Inactivos":
            filtered_data = filtered_data[
                (filtered_data['EVALASIGN'].isin(INACTIVE_EVALUATORS.get(selected_module, []))) &
                (~filtered_data['EVALASIGN'].isin(VULNERABILIDAD_EVALUATORS.get(selected_module, []))) &
                (filtered_data['EVALASIGN'] != 'SUSPENDIDA')
            ]
        elif view_type == "Vulnerabilidad":
            filtered_data = filtered_data[
                filtered_data['EVALASIGN'].isin(VULNERABILIDAD_EVALUATORS.get(selected_module, []))
            ]

        # Si no hay datos después del filtrado
        if filtered_data.empty:
            st.info("No se encontraron expedientes pendientes con los filtros seleccionados")
            return

        # Preparar datos para la tabla principal
        if len(selected_years) == 1:
            # Vista por meses para un solo año
            pending_table = filtered_data.groupby(['EVALASIGN', 'Mes']).agg({
                'NumeroTramite': 'count'
            }).reset_index()
            
            pending_table = pending_table.pivot(
                index='EVALASIGN',
                columns='Mes',
                values='NumeroTramite'
            ).fillna(0)
            
            # Renombrar columnas de meses
            month_names = {
                1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
            }
            pending_table = pending_table.rename(columns=month_names)
            
        else:
            pending_table = filtered_data.groupby(['EVALASIGN', 'Anio']).agg({
                'NumeroTramite': 'count'
            }).reset_index()
            
            pending_table = pending_table.pivot(
                index='EVALASIGN',
                columns='Anio',
                values='NumeroTramite'
            ).fillna(0)
        
        pending_table['TOTAL'] = pending_table.sum(axis=1)
        pending_table = pending_table.sort_values('TOTAL', ascending=False)
        pending_table = pending_table.astype(int)

        # Mostrar métricas en paneles tipo dashboard
        total_data = data[data['Evaluado'] == 'NO']
        
        # Calcular métricas
        pendientes_asignados = total_data[
            total_data['EVALASIGN'].notna() & 
            (total_data['EVALASIGN'] != '')
        ]['NumeroTramite'].count()
        
        pendientes_no_asignados = total_data[
            total_data['EVALASIGN'].isna() | 
            (total_data['EVALASIGN'] == '')
        ]['NumeroTramite'].count()

        # Mostrar métricas en un diseño de dashboard
        st.markdown("### 📊 Panel de Control de Pendientes")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "📋 Expedientes Pendientes Asignados",
                f"{pendientes_asignados:,d}",
                help="Expedientes con evaluador asignado pendientes de evaluación"
            )
        with col2:
            st.metric(
                "⚠️ Expedientes Pendientes No Asignados",
                f"{pendientes_no_asignados:,d}",
                help="Expedientes sin evaluador asignado"
            )

        # Mostrar tabla principal
        st.markdown("### Detalle de Pendientes por Evaluador")
        st.dataframe(
            pending_table,
            use_container_width=True,
            height=400,
            column_config={
                col: st.column_config.NumberColumn(
                    col,
                    format="%d",
                    width="small"
                ) for col in pending_table.columns
            }
        )

        # Tabla resumen por tipo y año
        st.markdown("### Resumen General por Año")
        
        summary_data = data[data['Evaluado'] == 'NO'].copy()
        
        def get_status(row):
            try:
                if pd.isna(row['EVALASIGN']) or str(row['EVALASIGN']).strip() == '':
                    return 'No Asignado'
                elif row['EVALASIGN'] in VULNERABILIDAD_EVALUATORS.get(selected_module, []):
                    return 'Vulnerabilidad'
                elif str(row['EVALASIGN']) == 'SUSPENDIDA':
                    return 'Suspendida'
                elif row['EVALASIGN'] in INACTIVE_EVALUATORS.get(selected_module, []):
                    return 'Inactivos'
                else:
                    return 'Activos'
            except Exception as e:
                print(f"Error en get_status: {str(e)}, valor: {row['EVALASIGN']}")
                return 'No Asignado'

        summary_data['Estado'] = summary_data.apply(get_status, axis=1)
        
        try:
            # Asegurar que Anio sea un valor válido
            summary_data['Anio'] = summary_data['Anio'].fillna(0).astype(int).astype(str)
            
            # Crear tabla pivote
            summary_table = pd.pivot_table(
                summary_data,
                values='NumeroTramite',
                index='Estado',
                columns='Anio',
                aggfunc='count',
                fill_value=0
            )
            
            # Ordenar las columnas cronológicamente
            summary_table = summary_table.reindex(sorted(summary_table.columns), axis=1)
            
            # Agregar columna de total
            summary_table['TOTAL'] = summary_table.sum(axis=1)
            
            # Convertir todos los valores a enteros
            summary_table = summary_table.astype(int)
            
            # Ordenar el índice para mantener un orden consistente
            desired_order = ['Activos', 'Inactivos', 'No Asignado', 'Suspendida', 'Vulnerabilidad']
            summary_table = summary_table.reindex(desired_order)
            
            # Mostrar la tabla
            st.dataframe(
                summary_table,
                use_container_width=True,
                column_config={
                    str(col): st.column_config.NumberColumn(
                        str(col),
                        format="%d",
                        width="small"
                    ) for col in summary_table.columns
                }
            )

        except Exception as e:
            st.error(f"Error al generar la tabla resumen: {str(e)}")
            print(f"Error detallado en tabla resumen: {str(e)}")
            # Mostrar información de debugging
            print("Columnas disponibles:", summary_data.columns.tolist())
            print("Tipos de datos:", summary_data.dtypes)
            print("Valores únicos en Anio:", summary_data['Anio'].unique())

    except Exception as e:
        st.error(f"Error al procesar los datos: {str(e)}")
        print(f"Error detallado: {str(e)}")