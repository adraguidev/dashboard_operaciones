import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
import plotly.graph_objects as go
import plotly.express as px
import time

def show_loading_progress(message: str):
    """
    Muestra una barra de progreso animada con mensaje personalizado.
    """
    progress_placeholder = st.empty()
    progress_bar = st.progress(0)
    
    for i in range(100):
        progress_placeholder.text(f"{message} {i+1}%")
        progress_bar.progress(i + 1)
        time.sleep(0.01)
    
    progress_placeholder.empty()
    progress_bar.empty()

def render_metric_card(title, value, delta=None, help_text=None):
    """
    Renderiza una tarjeta de métrica con estilo personalizado y animación.
    """
    st.markdown(f"""
    <style>
    .metric-card {{
        background: linear-gradient(135deg, #ffffff 0%, #f5f7fa 100%);
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #e0e5eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        animation: fadeIn 0.5s ease-out;
    }}
    .metric-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .metric-title {{
        color: #2c3e50;
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }}
    .metric-value {{
        color: #FF4B4B;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }}
    .metric-delta {{
        font-size: 0.9rem;
        font-weight: 500;
        padding: 0.2rem 0.5rem;
        border-radius: 15px;
        display: inline-block;
    }}
    .metric-help {{
        color: #666;
        font-size: 0.8rem;
        margin-top: 0.5rem;
    }}
    </style>
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        {f'<div class="metric-delta" style="background-color: {"#e6f4ea" if float(delta.replace("%","")) > 0 else "#fce8e6"}; color: {"#137333" if float(delta.replace("%","")) > 0 else "#a50e0e"};">{delta}</div>' if delta else ''}
        {f'<div class="metric-help">{help_text}</div>' if help_text else ''}
    </div>
    """, unsafe_allow_html=True)

def render_table(data, title, height=400):
    """
    Renderiza una tabla mejorada usando AgGrid con estilos personalizados y optimizaciones.
    """
    st.markdown(f'<h3 style="color: #2c3e50; margin-bottom: 1rem;">{title}</h3>', unsafe_allow_html=True)
    
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
        paginationAutoPageSize=True,
        suppressScrollOnNewData=True,
        animateRows=True
    )
    
    grid_options = gb.build()
    
    custom_css = {
        ".ag-root-wrapper": {
            "border-radius": "10px",
            "border": "1px solid #e0e5eb"
        },
        ".ag-header-cell": {
            "background-color": "#f8f9fa"
        },
        ".ag-header-cell-label": {
            "font-weight": "600",
            "color": "#2c3e50"
        },
        ".ag-cell": {
            "padding-left": "1rem",
            "padding-right": "1rem"
        },
        ".ag-row-hover": {
            "background-color": "#f5f7fa !important"
        },
        ".ag-row-selected": {
            "background-color": "#e8f0fe !important"
        }
    }
    
    return AgGrid(
        data,
        gridOptions=grid_options,
        height=height,
        theme='streamlit',
        custom_css=custom_css,
        enable_enterprise_modules=False,
        update_mode='value_changed',
        reload_data=False
    )

def create_plotly_chart(fig, title=None):
    """
    Aplica un estilo consistente y optimizado a los gráficos de Plotly.
    """
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(family="Arial, sans-serif", size=20),
            x=0.5,
            xanchor='center'
        ),
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
            x=1,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='rgba(0,0,0,0.1)',
            borderwidth=1
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linewidth=1,
            linecolor='rgba(0,0,0,0.2)',
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linewidth=1,
            linecolor='rgba(0,0,0,0.2)',
            tickfont=dict(size=10)
        ),
        hovermode='closest',
        transition_duration=500
    )
    
    # Optimizar el rendimiento del gráfico
    fig.update_traces(
        hovertemplate='<b>%{text}</b><br>' +
                     '%{xaxis.title.text}: %{x}<br>' +
                     '%{yaxis.title.text}: %{y}<extra></extra>'
    )
    
    return st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
    })

def render_info_card(title, content, icon=None):
    """
    Renderiza una tarjeta de información con estilo personalizado y animaciones.
    """
    st.markdown(f"""
    <style>
    .info-card {{
        background: linear-gradient(135deg, #ffffff 0%, #f5f7fa 100%);
        border-radius: 10px;
        padding: 1.5rem;
        border: 1px solid #e0e5eb;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
        animation: slideIn 0.5s ease-out;
    }}
    .info-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }}
    @keyframes slideIn {{
        from {{ opacity: 0; transform: translateX(-10px); }}
        to {{ opacity: 1; transform: translateX(0); }}
    }}
    .info-title {{
        color: #2c3e50;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}
    .info-content {{
        color: #4a5568;
        font-size: 1rem;
        line-height: 1.5;
    }}
    </style>
    <div class="info-card">
        <div class="info-title">{f'{icon} ' if icon else ''}{title}</div>
        <div class="info-content">{content}</div>
    </div>
    """, unsafe_allow_html=True)

def render_status_pill(status, positive_statuses=['Completado', 'Activo', 'OK']):
    """
    Renderiza un indicador de estado tipo pill con animación.
    """
    color = '#00c853' if status in positive_statuses else '#ff3d00'
    return f"""
    <style>
    @keyframes pulseStatus {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
        100% {{ transform: scale(1); }}
    }}
    </style>
    <span style="
        background-color: {color}22;
        color: {color};
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-block;
        animation: pulseStatus 2s infinite;
        transition: all 0.3s ease;
    ">
        {status}
    </span>
    """

def create_kpi_section(kpis):
    """
    Crea una sección de KPIs con múltiples métricas y animaciones.
    """
    st.markdown("""
    <style>
    .kpi-container {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(len(kpis))
    for i, (col, kpi) in enumerate(zip(cols, kpis)):
        with col:
            render_metric_card(
                title=kpi['title'],
                value=kpi['value'],
                delta=kpi.get('delta'),
                help_text=kpi.get('help_text')
            )