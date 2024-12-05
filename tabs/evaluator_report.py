import streamlit as st
import pandas as pd
from io import BytesIO

def render_evaluator_report_tab(data: pd.DataFrame):
    try:
        st.header("Reporte por Evaluador")
        
        # Validar datos
        if data is None or data.empty:
            st.error("No hay datos disponibles para mostrar")
            return

        # Asegurar que EVALASIGN no tiene valores None
        data['EVALASIGN'] = data['EVALASIGN'].fillna('')
        evaluators = sorted(data[data['EVALASIGN'] != '']['EVALASIGN'].unique())

        # Selección de evaluador
        selected_evaluator = st.selectbox(
            "Selecciona un Evaluador", 
            options=evaluators
        )

        # Selección de años
        available_years = sorted(data['Anio'].unique())
        selected_years = st.multiselect(
            "Selecciona el Año o Años", 
            options=available_years
        )

        # Selección de meses si hay años seleccionados
        selected_months = get_selected_months(data, selected_years) if selected_years else None

        # Filtrar y mostrar datos
        filtered_data = filter_evaluator_data(
            data, 
            selected_evaluator, 
            selected_years, 
            selected_months
        )

        # Mostrar resultados
        display_filtered_results(filtered_data)
    except Exception as e:
        st.error(f"Error al renderizar el reporte por evaluador: {e}")

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