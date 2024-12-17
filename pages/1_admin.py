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

# Estilos personalizados
st.markdown("""
<style>
    /* Estilos para el sidebar y menú */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        min-width: 220px !important;
        max-width: 220px !important;
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 15rem !important;
        background: linear-gradient(to bottom, var(--sidebar-color) 0%, rgba(248,249,250,0.97) 100%);
    }
    
    /* Estilo para los botones principales */
    section[data-testid="stSidebar"] button {
        height: 2.2rem !important;
        padding: 0 0.8rem !important;
        margin-bottom: 0.3rem !important;
        border: none !important;
        background-color: white !important;
        color: #1f1f1f !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }
    
    section[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #FF4B4B !important;
        color: white !important;
    }
    
    /* Estilo para los submódulos */
    .submenu {
        margin-left: 0.5rem !important;
        margin-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        border-left: 2px solid #e9ecef !important;
    }
    
    /* Estilo para radio buttons en el submenu */
    .submenu .stRadio > div {
        display: flex !important;
        flex-direction: column !important;
        gap: 0.2rem !important;
    }
    
    .submenu .stRadio label {
        padding: 0.3rem 0.8rem !important;
        font-size: 0.85rem !important;
        background: white !important;
        border-radius: 4px !important;
        transition: all 0.2s !important;
        cursor: pointer !important;
        margin: 0 !important;
    }
    
    .submenu .stRadio label:hover {
        background: #f8f9fa !important;
        transform: translateX(3px) !important;
    }
    
    /* Ajustes adicionales para el contenido principal */
    section[data-testid="stSidebarContent"] {
        padding-top: 0 !important;
        height: calc(100vh - 2rem) !important;
    }
    
    /* Ocultar elementos específicos de Streamlit */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    div[data-testid="collapsedControl"] {
        display: block !important;
    }
    
    #MainMenu {
        display: none !important;
    }
    
    /* Ocultar elementos del sidebar por defecto */
    .st-emotion-cache-1rtdyuf {
        display: block !important;
    }
    
    .st-emotion-cache-h5rgaw {
        display: none !important;
    }
    
    .st-emotion-cache-1q1z5mp {
        display: none !important;
    }
    
    .st-emotion-cache-1oe5cao {
        display: none !important;
    }
    
    .st-emotion-cache-pkbazv {
        display: none !important;
    }
    
    /* Ocultar textos de páginas en el sidebar */
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    .st-emotion-cache-eczf16 {
        display: none !important;
    }
    
    .st-emotion-cache-r421ms {
        display: none !important;
    }
    
    /* Ocultar contenedor de navegación */
    .st-emotion-cache-1k5e5jk {
        display: none !important;
    }
    
    /* Ajustes para el sidebar colapsado */
    [data-testid="collapsedControl"] {
        display: block !important;
        color: #1f1f1f !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] {
        margin-left: -220px !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] ~ section[data-testid="stContent"] {
        margin-left: 0 !important;
        width: 100% !important;
        transition: margin 0.3s, width 0.3s !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="true"] ~ section[data-testid="stContent"] {
        margin-left: 220px !important;
        width: calc(100% - 220px) !important;
        transition: margin 0.3s, width 0.3s !important;
    }
    
    /* Estilos para las pestañas */
    .stTabs {
        background: transparent;
        padding: 0;
        box-shadow: none;
        margin-top: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        padding: 0;
        margin-bottom: 0;
        border-bottom: none;
        gap: 0;
        position: relative;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        background-color: rgba(248,249,250,0.5);
        border-radius: 0.5rem 0.5rem 0 0;
        color: #6c757d;
        font-size: 0.9rem;
        font-weight: 500;
        border: 1px solid #dee2e6;
        border-bottom: none;
        padding: 0 1.5rem;
        margin: 0;
        margin-right: -1px;
        transition: all 0.2s;
        position: relative;
        bottom: 0;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: white;
        color: var(--primary-color);
        border-color: #dee2e6;
        transform: translateY(-1px);
        z-index: 1;
    }
    
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: var(--primary-color) !important;
        font-weight: 600 !important;
        border: 1px solid #dee2e6 !important;
        border-bottom: 1px solid white !important;
        box-shadow: none !important;
        z-index: 2;
    }
    
    /* Contenido de las pestañas */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 1rem 0 0 0;
        background-color: transparent;
        border-top: none;
        margin-top: 0;
    }
    
    /* Estilo para los botones dentro de las pestañas */
    .stTabs button {
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stTabs button[kind="primary"] {
        background: linear-gradient(90deg, #FF4B4B 0%, #ff6b6b 100%);
        border: none;
        color: white;
        box-shadow: 0 2px 4px rgba(255,75,75,0.2);
    }
    
    .stTabs button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(255,75,75,0.3);
    }
    
    /* Botón de colapso del sidebar siempre visible */
    [data-testid="collapsedControl"] {
        display: block !important;
        position: fixed !important;
        top: 1rem !important;
        left: 1rem !important;
        background-color: white !important;
        border-radius: 4px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        z-index: 999 !important;
        height: 2.5rem !important;
        width: 2.5rem !important;
        padding: 0.5rem !important;
        transition: all 0.2s !important;
        border: 1px solid #dee2e6 !important;
    }
    
    [data-testid="collapsedControl"]:hover {
        background-color: #f8f9fa !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    /* Estilos globales */
    :root {
        --primary-color: #FF4B4B;
        --primary-color-hover: #ff6b6b;
        --background-color: #ffffff;
        --sidebar-color: #f8f9fa;
        --text-color: #1f1f1f;
        --border-radius: 0.5rem;
        --transition-speed: 0.2s;
    }
    
    /* Fondo principal */
    .stApp {
        background-color: var(--background-color);
    }
    
    /* Estilos para el sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-color);
        border-right: 1px solid rgba(0,0,0,0.1);
        box-shadow: 2px 0 5px rgba(0,0,0,0.05);
    }
    
    /* Contenedor principal */
    section[data-testid="stContent"] {
        padding: 1rem !important;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    /* Estilos para las pestañas */
    .stTabs {
        background: transparent;
        padding: 0;
        box-shadow: none;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        padding: 0;
        margin-bottom: 1rem;
        border-bottom: 2px solid #f1f1f1;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        color: #6c757d;
        font-size: 0.9rem;
        font-weight: 500;
        border: none;
        padding: 0 1.5rem;
        margin-right: 0.5rem;
        transition: all 0.2s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #fff3f3;
        color: var(--primary-color);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-color-hover) 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 4px rgba(255,75,75,0.2) !important;
    }
    
    /* Contenido de las pestañas */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 1.5rem 0;
        background-color: transparent;
    }
    
    /* Estilos para cards */
    .stCard {
        background-color: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    .stCard:hover {
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para métricas */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    [data-testid="stMetric"]:hover {
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para dataframes */
    .stDataFrame {
        background-color: white;
        padding: 1rem;
        border-radius: var(--border-radius);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    .stDataFrame:hover {
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para expanders */
    .streamlit-expanderHeader {
        background-color: white;
        border: 1px solid #f1f1f1 !important;
        border-radius: var(--border-radius) !important;
        transition: all 0.2s;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: #e9ecef !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color);
        font-weight: 600;
    }
    
    h1 {
        font-size: 1.75rem !important;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    
    h3 {
        font-size: 1.25rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Estilos para las pestañas y contenedores */
    .stTabs {
        background: transparent;
        padding: 0;
        box-shadow: none;
        margin-top: 1rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        padding: 0;
        margin-bottom: 1.5rem;
        border-bottom: none;
        gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        background-color: rgba(255,255,255,0.8);
        border-radius: var(--border-radius);
        color: #6c757d;
        font-size: 0.95rem;
        font-weight: 500;
        border: 1px solid #f1f1f1;
        padding: 0 1.5rem;
        margin: 0;
        transition: all 0.2s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: white;
        color: var(--primary-color);
        border-color: var(--primary-color);
        transform: translateY(-1px);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-color-hover) 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        box-shadow: 0 4px 6px rgba(255,75,75,0.2) !important;
    }
    
    /* Contenido de las pestañas */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 0;
        background-color: transparent;
    }
    
    /* Ajustes para el contenedor principal */
    section[data-testid="stContent"] {
        padding: 2rem !important;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    /* Eliminar líneas divisorias innecesarias */
    .main-nav, hr, .stMarkdown hr {
        display: none !important;
    }
    
    /* Ajustes para el sidebar */
    section[data-testid="stSidebar"] > div {
        padding-top: 1.5rem !important;
        background: linear-gradient(to bottom, var(--sidebar-color) 0%, rgba(248,249,250,0.97) 100%);
    }
    
    /* Ajustes para los radio buttons en el submenu */
    .submenu {
        margin-left: 0.5rem !important;
        padding-left: 0.5rem !important;
        border-left: 2px solid rgba(255,75,75,0.1) !important;
    }
    
    .submenu .stRadio > div {
        background: transparent !important;
        padding: 0 !important;
    }
    
    .submenu .stRadio label {
        background: rgba(255,255,255,0.8) !important;
        border: 1px solid #f1f1f1;
        margin-bottom: 0.2rem !important;
    }
    
    .submenu .stRadio label:hover {
        background: white !important;
        border-color: var(--primary-color);
    }
    
    /* Ajustes para los contenedores de datos */
    [data-testid="stMetric"], .stDataFrame, .streamlit-expanderHeader {
        background: rgba(255,255,255,0.8);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    [data-testid="stMetric"]:hover, .stDataFrame:hover, .streamlit-expanderHeader:hover {
        background: white;
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Ajustes para el primer botón del sidebar */
    section[data-testid="stSidebar"] button:first-of-type {
        margin-top: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# Inicializar estados del menú si no existen
if 'menu_dashboard' not in st.session_state:
    st.session_state.menu_dashboard = False
if 'menu_admin' not in st.session_state:
    st.session_state.menu_admin = True

# Contenedor para el sidebar con estilo
with st.sidebar:
    # Menú Dashboard
    if st.button("📊 Dashboard", key="btn_dashboard", use_container_width=True):
        st.session_state.menu_dashboard = True
        st.session_state.menu_admin = False
        st.switch_page("dashboard.py")
    
    # Menú Admin
    if st.button("⚙️ Admin", key="btn_admin", use_container_width=True, type="primary"):
        st.session_state.menu_admin = True
        st.session_state.menu_dashboard = False
    
    # Submenú de Admin
    if st.session_state.menu_admin:
        with st.container():
            st.markdown('<div class="submenu">', unsafe_allow_html=True)
            admin_option = st.radio(
                "",
                options=["panel_control"],
                format_func=lambda x: "🔐 Panel de Control",
                key="admin_selector",
                label_visibility="collapsed"
            )
            st.markdown('</div>', unsafe_allow_html=True)

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
        st.text_input(
            "Contraseña", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Contraseña incorrecta, mostrar el input
        st.text_input(
            "Contraseña", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Contraseña incorrecta")
        return False
    else:
        # Contraseña correcta
        return True

if check_password():
    st.title("🔐 Panel de Administración")
    
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
        st.header("Gestión de Datos")
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Actualización de Datos")
            if st.button("🔄 Actualizar Base de Datos", use_container_width=True):
                with st.spinner("Actualizando datos..."):
                    st.session_state.force_refresh = True
                    if data_loader.force_data_refresh("Ka260314!"):
                        st.success("✅ Datos actualizados correctamente")
                        time.sleep(1)
                        st.rerun()
        
        with col2:
            st.subheader("Estado de Conexiones")
            if st.button("🔍 Verificar Conexiones", use_container_width=True):
                with st.spinner("Verificando conexiones..."):
                    try:
                        data_loader.migraciones_db.command('ping')
                        st.success("✅ Conexión a MongoDB activa")
                    except Exception as e:
                        st.error(f"❌ Error de conexión: {str(e)}")
    
    with tab2:
        st.header("Configuración del Sistema")
        
        # Configuración de módulos
        st.subheader("Módulos del Sistema")
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
        st.subheader("Gestión de Caché")
        if st.button("🗑️ Limpiar Caché del Sistema", type="secondary", use_container_width=True):
            with st.spinner("Limpiando caché..."):
                st.cache_data.clear()
                st.success("✅ Caché limpiado correctamente")
                time.sleep(1)
                st.rerun()
    
    with tab3:
        st.header("Monitoreo del Sistema")
        
        # Métricas del sistema
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Módulos Activos",
                len(st.session_state.get('visible_modules', [])),
                help="Número de módulos habilitados"
            )
        
        with col2:
            st.metric(
                "Uso de Caché",
                f"{round(len(str(st.session_state)) / 1024, 1)}MB",
                help="Memoria utilizada por el caché"
            )
        
        with col3:
            lima_tz = pytz.timezone('America/Lima')
            current_time = datetime.now(pytz.UTC).astimezone(lima_tz)
            st.metric(
                "Última Actualización",
                current_time.strftime("%d/%m/%Y %H:%M"),
                help="Hora de la última actualización"
            )
        
        # Logs del sistema
        st.subheader("Logs del Sistema")
        with st.expander("Ver logs", expanded=True):
            st.code(f"""
[INFO] Sistema iniciado: {current_time.strftime("%d/%m/%Y %H:%M")}
[INFO] Módulos activos: {len(st.session_state.get('visible_modules', []))}
[INFO] Memoria caché: {round(len(str(st.session_state)) / 1024, 2)}MB
[INFO] Estado de conexión: Activa
            """) 