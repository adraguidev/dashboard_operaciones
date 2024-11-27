
from st_aggrid import AgGrid, GridOptionsBuilder
import streamlit as st

# Theme configuration for a unified design
theme = {
    "primary_color": "#4CAF50",
    "secondary_color": "#FFC107",
    "font_family": "Arial, sans-serif",
    "dark_mode": False,  # Toggle for dark mode
}

def apply_theme():
    """
    Apply global styling, including dark mode.
    """
    if theme["dark_mode"]:
        st.markdown(
            f"""
            <style>
            body {{
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: {theme["font_family"]};
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <style>
            body {{
                background-color: #FFFFFF;
                color: #000000;
                font-family: {theme["font_family"]};
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

def render_table(data, title):
    """
    Render an interactive table using AgGrid with enhanced features.
    """
    apply_theme()
    st.subheader(title)

    # Prepare the data for display
    data_for_display = data.copy()
    data_for_display.fillna(0, inplace=True)

    # Configure AgGrid options
    gb = GridOptionsBuilder.from_dataframe(data_for_display)
    gb.configure_pagination(enabled=True, paginationAutoPageSize=False, paginationPageSize=10)
    gb.configure_default_column(editable=False, filterable=True, sortable=True)
    gb.configure_column("EVALASIGN", width=200)
    for col in data_for_display.columns:
        if col != "EVALASIGN":
            gb.configure_column(col, width=100)
    grid_options = gb.build()
    AgGrid(data_for_display, gridOptions=grid_options, editable=False, fit_columns_on_grid_load=True)
