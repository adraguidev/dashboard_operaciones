from st_aggrid import AgGrid, GridOptionsBuilder

def render_table(data, title):
    """
    Renderizar tabla en Streamlit usando AgGrid con valores nulos reemplazados por 0 solo para visualización.
    """
    import streamlit as st
    st.subheader(title)
    
    # Crear una copia de los datos para evitar modificar el original
    data_for_display = data.copy()
    
    # Reemplazar valores nulos en columnas categóricas
    for col in data_for_display.select_dtypes(['category']).columns:
        data_for_display[col] = data_for_display[col].cat.add_categories([0]).fillna(0)
    
    # Reemplazar valores nulos en otras columnas
    data_for_display.fillna(0, inplace=True)
    
    # Configurar AgGrid
    gb = GridOptionsBuilder.from_dataframe(data_for_display)
    gb.configure_column("EVALASIGN", width=200)
    for col in data_for_display.columns:
        if col != "EVALASIGN":
            gb.configure_column(col, width=100)
    grid_options = gb.build()
    AgGrid(data_for_display, gridOptions=grid_options, editable=False, fit_columns_on_grid_load=True)
