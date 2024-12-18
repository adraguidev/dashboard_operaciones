import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
import plotly.graph_objects as go
import plotly.express as px

def render_metric_card(title, value, delta=None, help_text=None):
    """
    Renderiza una tarjeta de métrica con estilo personalizado.
    """
    st.markdown("""
    <style>
    .stCard:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.15);
    }
    .tooltip:hover .tooltiptext {
        visibility: visible !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="stCard" style="
        background: linear-gradient(to bottom right, white, #fafafa);
        border-radius: 0.75rem;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.2s ease;
        border: 1px solid rgba(0, 0, 0, 0.05);
        cursor: default;
    ">
        <div class="tooltip" style="position: relative;">
            <h4 style="
                color: #1f2937;
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            ">
                {title}
                {f'<span style="color: #6b7280; font-size: 0.875rem;">ℹ️</span>' if help_text else ''}
            </h4>
            {f'<span class="tooltiptext" style="
                visibility: hidden;
                background-color: #1f2937;
                color: white;
                text-align: center;
                padding: 0.75rem 1rem;
                border-radius: 0.5rem;
                position: absolute;
                z-index: 1;
                bottom: 125%;
                left: 50%;
                transform: translateX(-50%);
                font-size: 0.875rem;
                width: max-content;
                max-width: 300px;
                opacity: 0;
                transition: all 0.2s ease;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.1);
            ">{help_text}</span>' if help_text else ''}
        </div>
        <h2 style="
            color: #FF4B4B;
            margin: 0.75rem 0;
            font-size: 1.75rem;
            font-weight: 700;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        ">{value}</h2>
        {f'<p style="
            color: {"#00c853" if float(delta.replace("%","")) > 0 else "#ff3d00"};
            font-size: 1rem;
            font-weight: 500;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.25rem;
            text-shadow: 0 1px 1px rgba(0,0,0,0.05);
        ">
            <span style="
                font-size: 1.25rem;
                display: inline-flex;
                align-items: center;
                background-color: {"rgba(0,200,83,0.1)" if float(delta.replace("%","")) > 0 else "rgba(255,61,0,0.1)"};
                padding: 0.125rem;
                border-radius: 0.25rem;
            ">{"↑" if float(delta.replace("%","")) > 0 else "↓"}</span>
            {delta}
        </p>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)

def render_table(data, title, height=400):
    """
    Renderiza una tabla mejorada usando AgGrid con estilos personalizados.
    """
    st.markdown("""
    <style>
    .table-header:hover {
        background-color: #f8fafc;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="stCard table-header" style="
        background: linear-gradient(to bottom right, white, #fafafa);
        border-radius: 0.75rem;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.2s ease;
    ">
        <h3 style="
            color: #1f2937;
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        ">
            <span>📊</span>
            {title}
        </h3>
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
        paginationAutoPageSize=True,
        suppressMovableColumns=True,
        rowSelection='multiple',
        rowMultiSelectWithClick=True
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
            ".ag-row-hover": {
                "background-color": "rgba(0,0,0,0.02) !important"
            },
            ".ag-row-selected": {
                "background-color": "rgba(255,75,75,0.1) !important"
            },
            ".ag-row": {
                "border-bottom": "1px solid rgba(0,0,0,0.05)",
                "transition": "all 0.2s"
            },
            ".ag-header": {
                "border-bottom": "2px solid rgba(0,0,0,0.1)",
                "background-color": "#f8fafc"
            },
            ".ag-header-cell:hover": {
                "background-color": "#f1f5f9"
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
        margin=dict(l=20, r=20, t=50, b=20),
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
            bgcolor='rgba(255,255,255,0.9)',
            bordercolor='rgba(0,0,0,0.1)',
            borderwidth=1,
            font=dict(size=11)
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linewidth=1,
            linecolor='rgba(0,0,0,0.2)',
            tickfont=dict(size=10),
            title_font=dict(size=12, color='#4b5563')
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(0,0,0,0.1)',
            showline=True,
            linewidth=1,
            linecolor='rgba(0,0,0,0.2)',
            tickfont=dict(size=10),
            title_font=dict(size=12, color='#4b5563')
        ),
        hoverlabel=dict(
            bgcolor='white',
            font_size=12,
            font_family="Arial, sans-serif"
        )
    )
    return st.plotly_chart(fig, use_container_width=True)

def render_info_card(title, content, icon=None):
    """
    Renderiza una tarjeta de información con estilo personalizado.
    """
    st.markdown("""
    <style>
    .info-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.15);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="stCard info-card" style="
        background: linear-gradient(to bottom right, white, #fafafa);
        border-radius: 0.75rem;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border: 1px solid rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
        cursor: default;
    ">
        <h4 style="
            color: #1f2937;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        ">
            {f'<span style="color: #FF4B4B;">{icon}</span>' if icon else ''}
            {title}
        </h4>
        <p style="
            color: #4b5563;
            font-size: 0.95rem;
            line-height: 1.6;
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
        gap: 0.375rem;
        justify-content: center;
        border: 1px solid {color}30;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    ">
        <span style="
            width: 0.5rem;
            height: 0.5rem;
            background-color: {color};
            border-radius: 50%;
            display: inline-block;
        "></span>
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
    .stMarkdown {
        height: 100%;
    }
    .stMarkdown > div {
        height: 100%;
    }
    .stCard {
        height: 100%;
        display: flex;
        flex-direction: column;
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