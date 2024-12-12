import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
import plotly.graph_objects as go
import plotly.express as px

def render_metric_card(title, value, delta=None, help_text=None):
    """
    Renderiza una tarjeta de métrica con estilo personalizado.
    """
    st.markdown(f"""
    <div class="stCard">
        <div class="tooltip">
            <h4>{title}</h4>
            {f'<span class="tooltiptext">{help_text}</span>' if help_text else ''}
        </div>
        <h2 style="color: #FF4B4B; margin: 0.5rem 0;">{value}</h2>
        {f'<p style="color: {"#00c853" if float(delta.replace("%","")) > 0 else "#ff3d00"};">{delta}</p>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)

def render_table(data, title, height=400):
    """
    Renderiza una tabla mejorada usando AgGrid con estilos personalizados.
    """
    st.markdown(f'<div class="stCard"><h3>{title}</h3></div>', unsafe_allow_html=True)
    
    # Configurar AgGrid
    gb = GridOptionsBuilder.from_dataframe(data)
    gb.configure_default_column(
        resizable=True,
        filterable=True,
        sorteable=True,
        min_column_width=100
    )
    gb.configure_grid_options(
        domLayout='normal',
        rowHeight=35,
        headerHeight=40,
        enableRangeSelection=True,
        pagination=True,
        paginationAutoPageSize=True
    )
    
    grid_options = gb.build()
    
    return AgGrid(
        data,
        gridOptions=grid_options,
        height=height,
        theme='streamlit',
        custom_css={
            ".ag-header-cell-label": {
                "font-weight": "600",
                "color": "#1f2937"
            },
            ".ag-cell": {
                "padding-left": "1rem",
                "padding-right": "1rem"
            }
        }
    )

def create_plotly_chart(fig, title=None):
    """
    Aplica un estilo consistente a los gráficos de Plotly.
    """
    fig.update_layout(
        title=title,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="Arial, sans-serif"),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linewidth=1,
            linecolor='rgba(0,0,0,0.2)'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linewidth=1,
            linecolor='rgba(0,0,0,0.2)'
        )
    )
    return st.plotly_chart(fig, use_container_width=True)

def render_info_card(title, content, icon=None):
    """
    Renderiza una tarjeta de información con estilo personalizado.
    """
    st.markdown(f"""
    <div class="stCard">
        <h4>{f'{icon} ' if icon else ''}{title}</h4>
        <p>{content}</p>
    </div>
    """, unsafe_allow_html=True)

def render_status_pill(status, positive_statuses=['Completado', 'Activo', 'OK']):
    """
    Renderiza un indicador de estado tipo pill.
    """
    color = '#00c853' if status in positive_statuses else '#ff3d00'
    return f"""
    <span style="
        background-color: {color}22;
        color: {color};
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 500;
    ">
        {status}
    </span>
    """

def create_kpi_section(kpis):
    """
    Crea una sección de KPIs con múltiples métricas.
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            render_metric_card(
                title=kpi['title'],
                value=kpi['value'],
                delta=kpi.get('delta'),
                help_text=kpi.get('help_text')
            ) 