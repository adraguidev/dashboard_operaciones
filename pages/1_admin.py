import streamlit as st
import time
from datetime import datetime
import pytz
from src.services.data_loader import DataLoader
from src.services.system_monitor import SystemMonitor
from src.services.report_generator import ReportGenerator
import os

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
        padding: 1rem 0.5rem !important;
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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔄 Gestión de Datos",
        "📊 Monitoreo de Rendimiento",
        "📝 Logs Avanzados",
        "💾 Optimización",
        "📈 Reportes",
        "🔧 Mantenimiento"
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
    
    with tab2:
        st.header("📊 Monitoreo de Rendimiento")
        
        # Métricas en tiempo real
        metrics = st.session_state.system_monitor.get_system_metrics()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Tiempo de Respuesta",
                f"{metrics.get('response_time', 0):.0f}ms",
                f"{metrics.get('response_time_delta', 0):.0f}ms"
            )
        with col2:
            st.metric(
                "Uso de CPU",
                f"{metrics.get('cpu_usage', 0):.1f}%",
                f"{metrics.get('cpu_delta', 0):.1f}%"
            )
        with col3:
            st.metric(
                "Memoria RAM",
                f"{metrics.get('memory_used', 0):.1f}GB",
                f"{metrics.get('memory_delta', 0):.1f}GB"
            )
        
        # MongoDB Stats
        st.subheader("Estadísticas de MongoDB")
        mongo_stats = st.session_state.system_monitor.get_mongodb_stats()
        
        if mongo_stats:
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "Conexiones Activas",
                    mongo_stats.get('connections', {}).get('current', 0)
                )
            with col2:
                st.metric(
                    "Operaciones/min",
                    sum(mongo_stats.get('opcounters', {}).values()) // 60
                )
        
        # Estadísticas por módulo
        st.subheader("Rendimiento por Módulo")
        module_stats = []
        for module in MODULES:
            stats = st.session_state.system_monitor.get_collection_stats(
                MONGODB_COLLECTIONS.get(module, '')
            )
            if stats:
                module_stats.append({
                    'Módulo': MODULES[module],
                    'Tamaño (MB)': f"{stats['size']:.1f}",
                    'Documentos': stats['count'],
                    'Índices': stats['indexes']
                })
        
        if module_stats:
            st.dataframe(pd.DataFrame(module_stats), hide_index=True)
    
    with tab3:
        st.header("📝 Logs Avanzados")
        
        # Filtros de logs
        col1, col2, col3 = st.columns(3)
        with col1:
            log_type = st.selectbox("Tipo de Log", ["Todos", "Error", "Warning", "Info", "Debug"])
        with col2:
            log_module = st.selectbox("Módulo", ["Todos"] + list(MODULES.values()))
        with col3:
            log_date = st.date_input("Fecha")
        
        # Obtener y mostrar logs
        logs = st.session_state.system_monitor.get_system_logs(
            log_type=log_type if log_type != "Todos" else None,
            module=log_module if log_module != "Todos" else None,
            start_date=datetime.combine(log_date, datetime.min.time()),
            end_date=datetime.combine(log_date, datetime.max.time())
        )
        
        if logs:
            st.dataframe(
                pd.DataFrame(logs)[['timestamp', 'level', 'module', 'message']],
                hide_index=True
            )
        else:
            st.info("No hay logs para los filtros seleccionados")
        
        # Acciones de logs
        col1, col2 = st.columns(2)
        with col1:
            if st.download_button(
                "📥 Exportar Logs",
                data=pd.DataFrame(logs).to_csv(index=False).encode('utf-8'),
                file_name=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            ):
                st.success("Logs exportados correctamente")
        
        with col2:
            if st.button("🗑️ Limpiar Logs Antiguos"):
                with st.spinner("Limpiando logs antiguos..."):
                    deleted = st.session_state.system_monitor.clean_old_data(
                        'system_logs',
                        days=30
                    )
                    st.success(f"Se eliminaron {deleted} logs antiguos")
    
    with tab4:
        st.header("💾 Optimización de Datos")
        
        # Uso de almacenamiento
        st.subheader("Uso de Almacenamiento")
        storage_data = []
        for module in MODULES:
            stats = st.session_state.system_monitor.get_collection_stats(
                MONGODB_COLLECTIONS.get(module, '')
            )
            if stats:
                storage_data.append({
                    'Colección': MODULES[module],
                    'Tamaño (MB)': f"{stats['size']:.1f}",
                    'Documentos': stats['count'],
                    'Tamaño Promedio (KB)': f"{stats['avg_obj_size']:.1f}"
                })
        
        if storage_data:
            st.dataframe(pd.DataFrame(storage_data), hide_index=True)
        
        # Acciones de optimización
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Limpiar Datos Antiguos"):
                with st.spinner("Limpiando datos antiguos..."):
                    total_deleted = 0
                    for module in MODULES:
                        collection = MONGODB_COLLECTIONS.get(module, '')
                        if collection:
                            deleted = st.session_state.system_monitor.clean_old_data(
                                collection,
                                days=st.session_state.get('retention_days', 180)
                            )
                            total_deleted += deleted
                    st.success(f"Se eliminaron {total_deleted} documentos antiguos")
        
        with col2:
            if st.button("🔄 Reindexar Colecciones"):
                with st.spinner("Reindexando colecciones..."):
                    success = True
                    for module in MODULES:
                        collection = MONGODB_COLLECTIONS.get(module, '')
                        if collection:
                            if not st.session_state.system_monitor.optimize_collection(collection):
                                success = False
                                break
                    
                    if success:
                        st.success("Colecciones reindexadas correctamente")
                    else:
                        st.error("Error al reindexar algunas colecciones")
        
        # Configuración de retención
        st.subheader("Política de Retención")
        retention_days = st.slider(
            "Días de retención de datos",
            30, 365, st.session_state.get('retention_days', 180)
        )
        
        if st.button("💾 Guardar Configuración"):
            st.session_state.retention_days = retention_days
            st.success("Configuración guardada correctamente")
    
    with tab5:
        st.header("📈 Reportes del Sistema")
        
        # Generación de reportes
        st.subheader("Generar Reporte")
        col1, col2, col3 = st.columns(3)
        with col1:
            report_type = st.selectbox("Tipo de Reporte", [
                "Rendimiento del Sistema",
                "Errores y Advertencias",
                "Estadísticas de Uso"
            ])
        with col2:
            report_format = st.selectbox("Formato", ["PDF", "Excel", "CSV"])
        with col3:
            days = st.number_input("Días a incluir", 1, 90, 7)
        
        if st.button("📊 Generar Reporte"):
            with st.spinner("Generando reporte..."):
                if report_type == "Rendimiento del Sistema":
                    report_file = st.session_state.report_generator.generate_performance_report(
                        days=days,
                        format=report_format
                    )
                elif report_type == "Errores y Advertencias":
                    report_file = st.session_state.report_generator.generate_error_report(
                        days=days,
                        format=report_format
                    )
                else:  # Estadísticas de Uso
                    report_file = st.session_state.report_generator.generate_usage_report(
                        days=days,
                        format=report_format
                    )
                
                if report_file:
                    with open(report_file, 'rb') as f:
                        st.download_button(
                            "📥 Descargar Reporte",
                            data=f.read(),
                            file_name=os.path.basename(report_file),
                            mime="application/octet-stream"
                        )
                else:
                    st.error("Error al generar el reporte")
    
    with tab6:
        st.header("🔧 Mantenimiento")
        
        # Estado del sistema
        st.subheader("Estado del Sistema")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Uptime", st.session_state.system_monitor.get_uptime())
        with col2:
            st.metric("Versión", "1.0.0")
        with col3:
            mongo_status = "Operativo" if st.session_state.system_monitor.get_mongodb_stats() else "Error"
            st.metric("Estado MongoDB", mongo_status)
        
        # Tareas de mantenimiento
        st.subheader("Tareas de Mantenimiento")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Limpiar Caché"):
                with st.spinner("Limpiando caché..."):
                    st.cache_data.clear()
                    st.success("Caché limpiado correctamente")
        
        with col2:
            if st.button("💾 Backup Configuración"):
                with st.spinner("Realizando backup..."):
                    backup_file = st.session_state.system_monitor.backup_config()
                    if backup_file:
                        st.success(f"Backup guardado en: {backup_file}")
                    else:
                        st.error("Error al realizar el backup")
        
        # Historial de mantenimiento
        st.subheader("Historial de Mantenimiento")
        maintenance_logs = st.session_state.system_monitor.get_system_logs(
            log_type="Info",
            module="Maintenance",
            limit=10
        )
        
        if maintenance_logs:
            st.dataframe(
                pd.DataFrame(maintenance_logs)[['timestamp', 'message']],
                hide_index=True
            )
        else:
            st.info("No hay registros de mantenimiento") 