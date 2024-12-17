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
    /* Ocultar elementos específicos de Streamlit */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    div[data-testid="collapsedControl"] {
        display: none !important;
    }
    
    #MainMenu {
        display: none !important;
    }
    
    /* Ocultar elementos del sidebar por defecto */
    .st-emotion-cache-1rtdyuf {
        display: none !important;
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
    
    /* Ajustar el padding superior del sidebar */
    section[data-testid="stSidebar"] > div {
        padding-top: 0rem !important;
    }
    
    /* Estilo para el menú principal */
    .menu-title {
        color: #1f1f1f;
        font-size: 1rem;
        font-weight: 600;
        padding: 0.5rem;
        margin: 0;
        cursor: pointer;
        display: flex;
        align-items: center;
        background: white;
        border-radius: 5px;
        margin-bottom: 0.5rem;
        transition: all 0.2s;
    }
    
    .menu-title:hover {
        background: #f8f9fa;
    }
    
    .menu-title.active {
        background: #FF4B4B;
        color: white;
    }
    
    /* Estilo para los submódulos */
    .submenu {
        margin-left: 1rem;
        margin-bottom: 1rem;
        border-left: 2px solid #f1f1f1;
    }
    
    /* Eliminar el menú naranja superior */
    .main-nav {
        display: none !important;
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