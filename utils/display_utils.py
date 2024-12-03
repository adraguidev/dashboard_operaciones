import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder

def render_table(data, title):
    """
    Renderizar tabla en Streamlit usando AgGrid con valores nulos reemplazados por 0.
    """
    st.subheader(title)
    
    # Crear copia para no modificar los datos originales
    data_for_display = data.copy()
    
    # Reemplazar valores nulos en columnas categóricas
    for col in data_for_display.select_dtypes(['category']).columns:
        data_for_display[col] = data_for_display[col].cat.add_categories([0]).fillna(0)
    
    # Reemplazar otros valores nulos
    data_for_display.fillna(0, inplace=True)
    
    # Configurar AgGrid
    gb = GridOptionsBuilder.from_dataframe(data_for_display)
    configure_grid_columns(gb, data_for_display)
    grid_options = gb.build()
    
    AgGrid(
        data_for_display, 
        gridOptions=grid_options, 
        editable=False, 
        fit_columns_on_grid_load=True
    )

def configure_grid_columns(grid_builder, data):
    """
    Configurar columnas para AgGrid.
    """
    grid_builder.configure_column("EVALASIGN", width=200)
    for col in data.columns:
        if col != "EVALASIGN":
            grid_builder.configure_column(col, width=100)

def format_percentage(value):
    """
    Formatear valor como porcentaje.
    """
    return f"{value:.2f}%"

def format_date(date):
    """
    Formatear fecha en formato dd/mm/yyyy.
    """
    return date.strftime('%d/%m/%Y')

def show_metric_card(title, value, delta=None, delta_color="normal"):
    """
    Mostrar tarjeta de métrica con formato consistente.
    """
    if delta is not None:
        st.metric(title, value, delta, delta_color=delta_color)
    else:
        st.metric(title, value) 