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
    /* Ocultar solo elementos específicos de Streamlit */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    #MainMenu {
        display: none !important;
    }
    
    /* Ajustes para el sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        min-width: 220px !important;
        max-width: 220px !important;
        position: relative;
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 3rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        background: linear-gradient(to bottom, var(--sidebar-color) 0%, rgba(248,249,250,0.97) 100%);
        height: 100vh;
        position: fixed;
        width: 220px;
    }
    
    /* Ajustes para el botón de colapso */
    button[kind="secondary"][data-testid="baseButton-secondary"] {
        position: fixed !important;
        top: 0.5rem !important;
        left: 0.5rem !important;
        background-color: white !important;
        border-radius: 4px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        z-index: 999 !important;
        height: 2rem !important;
        width: 2rem !important;
        padding: 0.2rem !important;
        transition: all 0.2s !important;
        margin: 0 !important;
    }
    
    /* Transiciones del sidebar */
    section[data-testid="stSidebar"][aria-expanded="false"] {
        margin-left: -220px !important;
        transition: margin-left 0.3s !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="true"] {
        margin-left: 0 !important;
        transition: margin-left 0.3s !important;
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
    
    /* Resto de los estilos... */
    // ... existing code ...
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