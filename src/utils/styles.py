import streamlit as st

def apply_global_styles():
    """
    Aplica estilos globales a la aplicación.
    """
    st.markdown("""
    <style>
    /* Estilos Globales */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Reset y variables */
    :root {
        --primary-color: #FF4B4B;
        --secondary-color: #2c3e50;
        --background-color: #ffffff;
        --surface-color: #f8f9fa;
        --text-color: #2c3e50;
        --border-color: #e0e5eb;
        --success-color: #00c853;
        --error-color: #ff3d00;
        --warning-color: #ffd600;
        --info-color: #2196f3;
    }

    /* Tipografía */
    * {
        font-family: 'Inter', sans-serif;
    }

    /* Contenedor principal */
    .main {
        padding: 1rem;
        max-width: 1200px;
        margin: 0 auto;
    }

    /* Animaciones Globales */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes slideUp {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    /* Estilos de Streamlit personalizados */
    .stButton>button {
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }

    .stButton>button:hover {
        background-color: #ff3333;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .stSelectbox {
        border-radius: 4px;
    }

    .stTextInput>div>div>input {
        border-radius: 4px;
    }

    /* Contenedores y Tarjetas */
    .container {
        background: var(--surface-color);
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        animation: fadeIn 0.5s ease-out;
    }

    .card {
        background: var(--background-color);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }

    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

    /* Tablas */
    .dataframe {
        border-collapse: collapse;
        width: 100%;
        margin: 1rem 0;
    }

    .dataframe th {
        background-color: var(--surface-color);
        color: var(--text-color);
        font-weight: 600;
        padding: 0.75rem 1rem;
        text-align: left;
        border-bottom: 2px solid var(--border-color);
    }

    .dataframe td {
        padding: 0.75rem 1rem;
        border-bottom: 1px solid var(--border-color);
    }

    .dataframe tr:hover {
        background-color: var(--surface-color);
    }

    /* Alertas y Notificaciones */
    .alert {
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
        animation: slideUp 0.3s ease-out;
    }

    .alert-success {
        background-color: #e8f5e9;
        color: var(--success-color);
        border-left: 4px solid var(--success-color);
    }

    .alert-error {
        background-color: #ffebee;
        color: var(--error-color);
        border-left: 4px solid var(--error-color);
    }

    .alert-warning {
        background-color: #fff8e1;
        color: var(--warning-color);
        border-left: 4px solid var(--warning-color);
    }

    .alert-info {
        background-color: #e3f2fd;
        color: var(--info-color);
        border-left: 4px solid var(--info-color);
    }

    /* Tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
    }

    .tooltip .tooltiptext {
        visibility: hidden;
        background-color: var(--secondary-color);
        color: white;
        text-align: center;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.3s;
    }

    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 500;
    }

    .badge-primary {
        background-color: var(--primary-color);
        color: white;
    }

    .badge-secondary {
        background-color: var(--secondary-color);
        color: white;
    }

    /* Loader */
    .loader {
        border: 3px solid var(--surface-color);
        border-radius: 50%;
        border-top: 3px solid var(--primary-color);
        width: 24px;
        height: 24px;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    </style>
    """, unsafe_allow_html=True)

def show_success_message(message: str):
    """
    Muestra un mensaje de éxito estilizado.
    """
    st.markdown(f"""
    <div class="alert alert-success">
        ✅ {message}
    </div>
    """, unsafe_allow_html=True)

def show_error_message(message: str):
    """
    Muestra un mensaje de error estilizado.
    """
    st.markdown(f"""
    <div class="alert alert-error">
        ❌ {message}
    </div>
    """, unsafe_allow_html=True)

def show_warning_message(message: str):
    """
    Muestra un mensaje de advertencia estilizado.
    """
    st.markdown(f"""
    <div class="alert alert-warning">
        ⚠️ {message}
    </div>
    """, unsafe_allow_html=True)

def show_info_message(message: str):
    """
    Muestra un mensaje informativo estilizado.
    """
    st.markdown(f"""
    <div class="alert alert-info">
        ℹ️ {message}
    </div>
    """, unsafe_allow_html=True)

def show_badge(text: str, type: str = "primary"):
    """
    Muestra un badge estilizado.
    """
    st.markdown(f"""
    <span class="badge badge-{type}">
        {text}
    </span>
    """, unsafe_allow_html=True)

def show_loader(message: str = "Cargando..."):
    """
    Muestra un loader estilizado con mensaje.
    """
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 0.5rem;">
        <div class="loader"></div>
        <span>{message}</span>
    </div>
    """, unsafe_allow_html=True) 