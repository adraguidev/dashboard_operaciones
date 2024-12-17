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
    /* Ocultar completamente el menú por defecto de Streamlit */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    div[data-testid="collapsedControl"] {
        display: none !important;
    }
    
    #MainMenu {
        display: none !important;
    }
    
    /* Estilos para el menú de navegación principal */
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 0;
        background-color: #f8f9fa;
    }
    
    /* Contenedor del menú principal */
    .main-nav {
        background: linear-gradient(to right, #FF4B4B, #ff6b6b);
        margin: -1rem -1rem 1rem -1rem;
        padding: 2rem 1rem 1rem 1rem;
    }
    
    /* Estilo para los enlaces del menú */
    .nav-link {
        color: white !important;
        text-decoration: none;
        padding: 0.5rem 1rem;
        margin: 0.2rem 0;
        border-radius: 5px;
        transition: all 0.2s;
        display: inline-block;
        width: auto;
        text-align: center;
        font-weight: 500;
        background: rgba(255,255,255,0.1);
    }
    
    .nav-link:hover {
        background: rgba(255,255,255,0.2);
        transform: translateX(5px);
    }
    
    .nav-link.active {
        background: white;
        color: #FF4B4B !important;
        font-weight: 600;
    }
    
    /* Ajustes para el contenido del sidebar */
    .sidebar-content {
        margin-top: 1rem;
    }
    
    /* Estilo para el título de la página */
    h1 {
        color: #1f1f1f;
        font-size: 2rem !important;
        font-weight: 600;
        margin-bottom: 2rem !important;
    }
</style>

<div class="main-nav">
    <a href="/" class="nav-link">📊 Dashboard</a>
    <a href="/admin" class="nav-link active">⚙️ Admin</a>
</div>
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