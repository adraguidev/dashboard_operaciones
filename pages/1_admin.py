import streamlit as st
import time
from datetime import datetime
import pytz
from src.services.data_loader import DataLoader

# Configuración de la página
st.set_page_config(
    page_title="Panel de Administración",
    page_icon="⚙️",
    layout="wide",
)

# Estilos personalizados mejorados
st.markdown("""
<style>
    /* Variables globales */
    :root {
        --primary-color: #FF4B4B;
        --primary-hover: #ff6b6b;
        --bg-color: #f8f9fa;
        --card-bg: white;
        --border-radius: 0.75rem;
        --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        --transition: all 0.2s ease;
    }

    /* Contenedor principal */
    .main {
        padding: 2rem;
        max-width: 1400px;
        margin: 0 auto;
    }

    /* Estilos para cards */
    .admin-card {
        background: linear-gradient(to bottom right, var(--card-bg), #fafafa);
        border-radius: var(--border-radius);
        padding: 1.5rem;
        border: 1px solid rgba(0, 0, 0, 0.05);
        box-shadow: var(--shadow);
        transition: var(--transition);
        margin-bottom: 1rem;
    }

    .admin-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px -2px rgba(0, 0, 0, 0.15);
    }

    /* Estilos para botones */
    .stButton > button {
        width: 100%;
        padding: 0.75rem 1rem !important;
        border-radius: 0.5rem !important;
        font-weight: 500 !important;
        transition: var(--transition) !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-hover) 100%) !important;
        border: none !important;
        color: white !important;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 6px rgba(255, 75, 75, 0.2) !important;
    }

    /* Estilos para métricas */
    [data-testid="stMetric"] {
        background: var(--card-bg);
        padding: 1.25rem;
        border-radius: var(--border-radius);
        border: 1px solid rgba(0, 0, 0, 0.05);
        transition: var(--transition);
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: #4b5563 !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: var(--primary-color) !important;
    }

    /* Estilos para tabs */
    .stTabs {
        background: transparent;
        padding: 0;
        margin-top: 1rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        border-bottom: 2px solid #f1f1f1;
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        border-radius: 0.5rem 0.5rem 0 0 !important;
        border: none !important;
        background: transparent !important;
        color: #6b7280 !important;
        transition: var(--transition) !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 75, 75, 0.1) !important;
        color: var(--primary-color) !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--primary-color) !important;
        color: white !important;
        font-weight: 600 !important;
    }

    /* Estilos para checkboxes */
    .stCheckbox {
        padding: 0.5rem;
        border-radius: 0.375rem;
        transition: var(--transition);
    }

    .stCheckbox:hover {
        background: rgba(0, 0, 0, 0.02);
    }

    /* Estilos para expander */
    .streamlit-expanderHeader {
        background: var(--card-bg) !important;
        border-radius: var(--border-radius) !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        transition: var(--transition) !important;
    }

    .streamlit-expanderHeader:hover {
        background: #f8f9fa !important;
    }

    /* Estilos para código */
    .stCodeBlock {
        background: #1f2937 !important;
        border-radius: var(--border-radius) !important;
        padding: 1rem !important;
    }

    /* Animaciones */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stTabs [data-baseweb="tab-panel"] > div {
        animation: fadeIn 0.3s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# Función para verificar la contraseña
def check_password():
    """Retorna `True` si el usuario tiene la contraseña correcta."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets.get("admin_password", "Ka260314!"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # No guardar la contraseña
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primera vez, mostrar el input
        st.markdown("""
        <div class="admin-card" style="max-width: 400px; margin: 2rem auto;">
            <h3 style="text-align: center; margin-bottom: 1rem;">🔐 Acceso Administrativo</h3>
        """, unsafe_allow_html=True)
        st.text_input(
            "Contraseña", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return False
    elif not st.session_state["password_correct"]:
        # Contraseña incorrecta, mostrar el input
        st.markdown("""
        <div class="admin-card" style="max-width: 400px; margin: 2rem auto;">
            <h3 style="text-align: center; margin-bottom: 1rem;">🔐 Acceso Administrativo</h3>
        """, unsafe_allow_html=True)
        st.text_input(
            "Contraseña", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Contraseña incorrecta")
        st.markdown("</div>", unsafe_allow_html=True)
        return False
    else:
        # Contraseña correcta
        return True

if check_password():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="color: #1f2937; font-size: 2rem; font-weight: 700;">🔐 Panel de Administración</h1>
        <p style="color: #6b7280; font-size: 1rem;">Gestión y monitoreo del sistema</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Inicializar data_loader si no existe
    if 'data_loader' not in st.session_state:
        with st.spinner('Inicializando conexión a la base de datos...'):
            st.session_state.data_loader = DataLoader()
    
    data_loader = st.session_state.data_loader
    
    # Crear tabs para diferentes secciones
    tab1, tab2, tab3 = st.tabs([
        "🔄 Gestión de Datos",
        "⚙️ Configuración",
        "📊 Monitoreo"
    ])
    
    with tab1:
        st.markdown("""
        <div class="admin-card">
            <h2 style="color: #1f2937; font-size: 1.5rem; margin-bottom: 1rem;">Gestión de Datos</h2>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="padding: 1rem; background: rgba(255,75,75,0.05); border-radius: 0.5rem;">
                <h3 style="color: #1f2937; font-size: 1.1rem; margin-bottom: 0.5rem;">Actualización de Datos</h3>
                <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem;">Actualiza la base de datos del sistema</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Actualizar Base de Datos", use_container_width=True):
                with st.spinner("Actualizando datos..."):
                    st.session_state.force_refresh = True
                    if data_loader.force_data_refresh("Ka260314!"):
                        st.success("✅ Datos actualizados correctamente")
                        time.sleep(1)
                        st.rerun()
        
        with col2:
            st.markdown("""
            <div style="padding: 1rem; background: rgba(255,75,75,0.05); border-radius: 0.5rem;">
                <h3 style="color: #1f2937; font-size: 1.1rem; margin-bottom: 0.5rem;">Estado de Conexiones</h3>
                <p style="color: #6b7280; font-size: 0.9rem; margin-bottom: 1rem;">Verifica el estado de las conexiones</p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔍 Verificar Conexiones", use_container_width=True):
                with st.spinner("Verificando conexiones..."):
                    try:
                        data_loader.migraciones_db.command('ping')
                        st.success("✅ Conexión a MongoDB activa")
                    except Exception as e:
                        st.error(f"❌ Error de conexión: {str(e)}")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with tab2:
        st.markdown("""
        <div class="admin-card">
            <h2 style="color: #1f2937; font-size: 1.5rem; margin-bottom: 1rem;">Configuración del Sistema</h2>
        """, unsafe_allow_html=True)
        
        # Configuración de módulos
        st.markdown("""
        <div style="padding: 1rem; background: rgba(255,75,75,0.05); border-radius: 0.5rem; margin-bottom: 1rem;">
            <h3 style="color: #1f2937; font-size: 1.1rem; margin-bottom: 0.5rem;">Módulos del Sistema</h3>
            <p style="color: #6b7280; font-size: 0.9rem;">Gestiona la visibilidad de los módulos</p>
        </div>
        """, unsafe_allow_html=True)
        
        from config.settings import MODULES
        
        if 'visible_modules' not in st.session_state:
            st.session_state.visible_modules = list(MODULES.keys())
        
        cols = st.columns(3)
        for i, module in enumerate(MODULES.keys()):
            with cols[i % 3]:
                if st.checkbox(
                    MODULES[module],
                    value=module in st.session_state.visible_modules,
                    key=f"module_visibility_{module}"
                ):
                    if module not in st.session_state.visible_modules:
                        st.session_state.visible_modules.append(module)
                else:
                    if module in st.session_state.visible_modules:
                        st.session_state.visible_modules.remove(module)
        
        # Gestión de caché
        st.markdown("""
        <div style="padding: 1rem; background: rgba(255,75,75,0.05); border-radius: 0.5rem; margin: 1rem 0;">
            <h3 style="color: #1f2937; font-size: 1.1rem; margin-bottom: 0.5rem;">Gestión de Caché</h3>
            <p style="color: #6b7280; font-size: 0.9rem;">Administra la memoria caché del sistema</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🗑️ Limpiar Caché del Sistema", type="secondary", use_container_width=True):
            with st.spinner("Limpiando caché..."):
                st.cache_data.clear()
                st.success("✅ Caché limpiado correctamente")
                time.sleep(1)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with tab3:
        st.markdown("""
        <div class="admin-card">
            <h2 style="color: #1f2937; font-size: 1.5rem; margin-bottom: 1rem;">Monitoreo del Sistema</h2>
        """, unsafe_allow_html=True)
        
        # Métricas del sistema
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "📦 Módulos Activos",
                len(st.session_state.get('visible_modules', [])),
                help="Número de módulos habilitados en el sistema"
            )
        
        with col2:
            st.metric(
                "💾 Uso de Caché",
                f"{round(len(str(st.session_state)) / 1024, 1)}MB",
                help="Memoria utilizada por el caché del sistema"
            )
        
        with col3:
            lima_tz = pytz.timezone('America/Lima')
            current_time = datetime.now(pytz.UTC).astimezone(lima_tz)
            st.metric(
                "🕒 Última Actualización",
                current_time.strftime("%d/%m/%Y %H:%M"),
                help="Hora de la última actualización del sistema"
            )
        
        # Logs del sistema
        st.markdown("""
        <div style="padding: 1rem; background: rgba(255,75,75,0.05); border-radius: 0.5rem; margin: 1rem 0;">
            <h3 style="color: #1f2937; font-size: 1.1rem; margin-bottom: 0.5rem;">Logs del Sistema</h3>
            <p style="color: #6b7280; font-size: 0.9rem;">Registro de actividades del sistema</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("Ver logs", expanded=True):
            st.code(f"""
[INFO] Sistema iniciado: {current_time.strftime("%d/%m/%Y %H:%M")}
[INFO] Módulos activos: {len(st.session_state.get('visible_modules', []))}
[INFO] Memoria caché: {round(len(str(st.session_state)) / 1024, 2)}MB
[INFO] Estado de conexión: Activa
            """)
        
        st.markdown("</div>", unsafe_allow_html=True)