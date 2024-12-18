import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
import plotly.graph_objects as go
import plotly.express as px

def render_metric_card(title, value, delta=None, help_text=None):
    """
    Renderiza una tarjeta de métrica con estilo personalizado.
    """
    st.markdown(f"""
    <div class="stCard" style="
        background: white;
        border-radius: 0.75rem;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
        border: 1px solid rgba(0, 0, 0, 0.05);
    ">
        <div class="tooltip" style="position: relative;">
            <h4 style="
                color: #1f2937;
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
            ">{title}</h4>
            {f'<span class="tooltiptext" style="
                visibility: hidden;
                background-color: #1f2937;
                color: white;
                text-align: center;
                padding: 0.5rem 1rem;
                border-radius: 0.375rem;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                transform: translateX(-50%);
                font-size: 0.875rem;
                width: max-content;
                max-width: 250px;
                opacity: 0;
                transition: opacity 0.3s;
            ">{help_text}</span>' if help_text else ''}
        </div>
        <h2 style="
            color: #FF4B4B;
            margin: 0.75rem 0;
            font-size: 1.75rem;
            font-weight: 700;
        ">{value}</h2>
        {f'<p style="
            color: {"#00c853" if float(delta.replace("%","")) > 0 else "#ff3d00"};
            font-size: 1rem;
            font-weight: 500;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.25rem;
        ">
            <span style="font-size: 1.25rem;">{"↑" if float(delta.replace("%","")) > 0 else "↓"}</span>
            {delta}
        </p>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)

def render_table(data, title, height=400):
    """
    Renderiza una tabla mejorada usando AgGrid con estilos personalizados.
    """
    st.markdown(f"""
    <div class="stCard" style="
        background: white;
        border-radius: 0.75rem;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    ">
        <h3 style="
            color: #1f2937;
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
        ">{title}</h3>
    </div>
    """, unsafe_allow_html=True)
    
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
                "color": "#1f2937",
                "font-size": "0.9rem"
            },
            ".ag-cell": {
                "padding-left": "1rem",
                "padding-right": "1rem",
                "font-size": "0.9rem"
            },
            ".ag-row": {
                "border-bottom": "1px solid rgba(0,0,0,0.05)"
            },
            ".ag-header": {
                "border-bottom": "2px solid rgba(0,0,0,0.1)"
            }
        }
    )

def create_plotly_chart(fig, title=None):
    """
    Aplica un estilo consistente a los gráficos de Plotly.
    """
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(
                size=18,
                color='#1f2937',
                family="Arial, sans-serif"
            ),
            x=0.5,
            xanchor='center'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(
            family="Arial, sans-serif",
            size=12,
            color='#4b5563'
        ),
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
        )
    )
    return st.plotly_chart(fig, use_container_width=True)

def render_info_card(title, content, icon=None):
    """
    Renderiza una tarjeta de información con estilo personalizado.
    """
    st.markdown(f"""
    <div class="stCard" style="
        background: white;
        border-radius: 0.75rem;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.05);
        transition: all 0.3s ease;
    ">
        <h4 style="
            color: #1f2937;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        ">{f'{icon} ' if icon else ''}{title}</h4>
        <p style="
            color: #4b5563;
            font-size: 0.95rem;
            line-height: 1.5;
            margin: 0;
        ">{content}</p>
    </div>
    """, unsafe_allow_html=True)

def render_status_pill(status, positive_statuses=['Completado', 'Activo', 'OK']):
    """
    Renderiza un indicador de estado tipo pill.
    """
    color = '#00c853' if status in positive_statuses else '#ff3d00'
    return f"""
    <span style="
        background-color: {color}15;
        color: {color};
        padding: 0.375rem 0.875rem;
        border-radius: 2rem;
        font-size: 0.875rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: 1px solid {color}30;
        transition: all 0.2s ease;
    ">
        {status}
    </span>
    """

def create_kpi_section(kpis):
    """
    Crea una sección de KPIs con múltiples métricas.
    """
    st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] {
        gap: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            render_metric_card(
                title=kpi['title'],
                value=kpi['value'],
                delta=kpi.get('delta'),
                help_text=kpi.get('help_text')
            )