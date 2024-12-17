import streamlit as st
from config.settings import MODULES, MONGODB_COLLECTIONS
from src.services.data_loader import DataLoader
from tabs.pending_reports import render_pending_reports_tab
from tabs.entry_analysis import render_entry_analysis_tab
from tabs.closing_analysis import render_closing_analysis_tab
from tabs.evaluator_report import render_evaluator_report_tab
from tabs.assignment_report import render_assignment_report_tab
import tabs.ranking_report as ranking_report
from modules.spe.spe_module import SPEModule
from src.utils.database import get_google_credentials
import time
from datetime import datetime, timedelta
import pytz

# Configuración de página
st.set_page_config(
    page_title="Dashboard USM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar la interfaz
st.markdown("""
<style>
    /* Ajustes para el botón de colapso */
    [data-testid="collapsedControl"] {
        position: fixed !important;
        left: 0 !important;
        top: 0.5rem !important;
        background: white !important;
        border-radius: 4px !important;
        width: 24px !important;
        height: 24px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 999 !important;
        border: 1px solid #e9ecef !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        margin: 0 !important;
        padding: 0 !important;
        cursor: pointer !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    section[data-testid="stSidebar"][aria-expanded="true"] ~ [data-testid="collapsedControl"] {
        left: 220px !important;
    }

    /* Ajustes para el sidebar y su contenido */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        min-width: 220px !important;
        max-width: 220px !important;
        transition: margin-left 0.3s !important;
    }

    section[data-testid="stSidebar"][aria-expanded="false"] {
        margin-left: -220px !important;
    }

    section[data-testid="stSidebar"][aria-expanded="false"] ~ section[data-testid="stContent"] {
        margin-left: 2rem !important;
        width: calc(100% - 2rem) !important;
        transition: margin 0.3s, width 0.3s !important;
    }

    section[data-testid="stSidebar"][aria-expanded="true"] ~ section[data-testid="stContent"] {
        margin-left: 220px !important;
        width: calc(100% - 220px) !important;
        transition: margin 0.3s, width 0.3s !important;
    }

    /* Estilos para el sidebar y menú */
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
    
    /* Estilo para la información de actualización */
    .update-info {
        font-size: 0.75rem !important;
        color: #6c757d !important;
        padding: 0.2rem 0.4rem !important;
        background-color: #e9ecef !important;
        border-radius: 0.2rem !important;
        margin-top: 0.5rem !important;
        display: inline-block !important;
        width: 100% !important;
        text-align: center !important;
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
</style>
""", unsafe_allow_html=True)

# Función para mostrar el header con información del usuario
def show_header():
    st.markdown("""
        <div style="margin-bottom: 0.5rem;">
            <h1>📊 Gestión de Expedientes</h1>
        </div>
    """, unsafe_allow_html=True)

# Función para verificar última actualización (cacheada por 5 minutos para no consultar constantemente)
@st.cache_data(ttl=300)
def get_current_time():
    """
    Retorna la hora actual en la zona horaria de Lima.
    """
    lima_tz = pytz.timezone('America/Lima')
    return datetime.now(pytz.UTC).astimezone(lima_tz)

# Función para generar hash de datos
def generate_data_hash(data):
    """
    Genera un hash único para los datos.
    Esto nos ayuda a detectar cambios reales en los datos.
    """
    import hashlib
    import json
    
    # Convertir DataFrame a string para hashear
    if hasattr(data, 'to_json'):
        data_str = data.to_json()
    else:
        data_str = json.dumps(str(data))
    
    return hashlib.md5(data_str.encode()).hexdigest()

# Función cacheada para cargar datos del módulo y su timestamp
@st.cache_data(ttl=None, persist="disk")  # Cache permanente y persistente en disco
def load_module_data_with_timestamp(selected_module):
    """
    Carga y cachea los datos del módulo junto con su timestamp.
    El caché persiste en disco y solo se invalida manualmente desde el panel de control.
    """
    # Verificar si hay una actualización forzada desde el panel de control
    if st.session_state.get('force_refresh', False):
        st.cache_data.clear()
        st.session_state.force_refresh = False
    
    data_loader = st.session_state.data_loader
    data = data_loader.load_module_data(selected_module)
    
    if data is not None:
        update_time = get_current_time()
        data_hash = generate_data_hash(data)
        
        return {
            'data': data,
            'update_time': update_time,
            'data_hash': data_hash,
            'load_time': update_time
        }
    return None

def get_module_data(selected_module, collection_name):
    """
    Función que maneja la lógica de carga de datos.
    """
    # Intentar cargar datos cacheados
    cached_data = load_module_data_with_timestamp(selected_module)
    
    if cached_data is not None:
        # Guardar el hash en session_state si no existe
        cache_key = f"{selected_module}_data_hash"
        previous_hash = st.session_state.get(cache_key)
        current_hash = cached_data['data_hash']
        
        # Actualizar el hash en session_state
        st.session_state[cache_key] = current_hash
        
        # Determinar si los datos realmente cambiaron
        data_changed = previous_hash != current_hash if previous_hash else True
        
        return cached_data['data'], cached_data['update_time'], data_changed
    
    return None, None, False

# Alternativa sin cache_resource
if 'data_loader' not in st.session_state:
    try:
        with st.spinner('🔄 Inicializando conexión a la base de datos...'):
            st.session_state.data_loader = DataLoader()
    except Exception as e:
        st.error(f"Error al inicializar DataLoader: {str(e)}")
        st.session_state.data_loader = None

# Función para obtener la fecha y hora actual en Lima
def get_lima_datetime():
    lima_tz = pytz.timezone('America/Lima')
    return datetime.now(pytz.UTC).astimezone(lima_tz)

# Función helper para mostrar spinner con progress bar
def show_loading_progress(message, action, show_fade_in=True):
    """
    Muestra un spinner con barra de progreso mientras se ejecuta una acción.
    
    Args:
        message: Mensaje a mostrar durante la carga
        action: Función a ejecutar
        show_fade_in: Si se debe mostrar el efecto fade-in
    Returns:
        El resultado de la acción ejecutada
    """
    with st.spinner(f'{message}...'):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
        
        if show_fade_in:
            st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        
        result = action()
        
        if show_fade_in:
            st.markdown('</div>', unsafe_allow_html=True)
        
        progress_bar.empty()
        return result

def main():
    try:
        data_loader = st.session_state.data_loader
        if data_loader is None:
            st.error("No se pudo inicializar la conexión a la base de datos.")
            return

        # Inicializar estados del menú si no existen
        if 'menu_dashboard' not in st.session_state:
            st.session_state.menu_dashboard = True
        if 'menu_admin' not in st.session_state:
            st.session_state.menu_admin = False
        if 'selected_module' not in st.session_state:
            st.session_state.selected_module = list(MODULES.keys())[0]

        # Contenedor para el sidebar con estilo
        with st.sidebar:
            # Menú Dashboard
            if st.button("📊 Dashboard", key="btn_dashboard", use_container_width=True, type="primary"):
                st.session_state.menu_dashboard = True
                st.session_state.menu_admin = False
            
            # Submódulos de Dashboard
            if st.session_state.menu_dashboard:
                with st.container():
                    st.markdown('<div class="submenu">', unsafe_allow_html=True)
                    selected_module = st.radio(
                        "",
                        options=st.session_state.get('visible_modules', list(MODULES.keys())),
                        format_func=lambda x: MODULES[x],
                        key="module_selector",
                        label_visibility="collapsed"
                    )
                    st.session_state.selected_module = selected_module
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                selected_module = st.session_state.selected_module
            
            # Menú Admin
            if st.button("⚙️ Admin", key="btn_admin", use_container_width=True):
                st.session_state.menu_admin = True
                st.session_state.menu_dashboard = False
                st.switch_page("pages/1_admin.py")
            
            # Mostrar última actualización si está disponible
            if 'update_time' in locals():
                st.markdown(
                    f'<div class="update-info">📅 {update_time.strftime("%d/%m/%Y %H:%M")}</div>',
                    unsafe_allow_html=True
                )

        # Inicializar la fecha de datos actual en session_state si no existe
        if 'current_data_date' not in st.session_state:
            st.session_state.current_data_date = None

        # Obtener credenciales de Google
        try:
            google_credentials = show_loading_progress(
                'Verificando credenciales',
                get_google_credentials,
                show_fade_in=False
            )
        except Exception as e:
            st.warning(f"No se pudieron obtener las credenciales de Google. SPE podría no funcionar correctamente.")
            google_credentials = None

        # Mostrar header
        show_header()

        # Cargar datos según el módulo seleccionado
        if selected_module == 'SPE':
            if google_credentials is None:
                st.error("No se pueden cargar datos de SPE sin credenciales de Google.")
                return
            
            spe = show_loading_progress(
                'Cargando módulo SPE',
                lambda: SPEModule()
            )
            spe.render_module()
            update_time = get_current_time()
            
        else:
            # Para otros módulos
            collection_name = MONGODB_COLLECTIONS.get(selected_module)
            if collection_name:
                data, update_time, _ = show_loading_progress(
                    f'📊 Cargando datos del módulo {MODULES[selected_module]}',
                    lambda: get_module_data(selected_module, collection_name),
                    show_fade_in=False
                )
                
                if data is None:
                    st.error("No se encontraron datos para este módulo en la base de datos.")
                    return

        # Agregar elementos adicionales al sidebar después de cargar los datos
        with st.sidebar:
            if 'show_update_form' in st.session_state:
                del st.session_state.show_update_form

        if selected_module != 'SPE':
            # Crear pestañas
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "Reporte de pendientes",
                "Ingreso de Expedientes",
                "Cierre de Expedientes",
                "Reporte por Evaluador",
                "Reporte de Asignaciones",
                "Ranking de Expedientes Trabajados"
            ])
            
            # Renderizar cada pestaña usando la función helper
            with tab1:
                show_loading_progress(
                    '📋 Cargando reporte de pendientes',
                    lambda: render_pending_reports_tab(data, selected_module)
                )
            
            with tab2:
                show_loading_progress(
                    '📈 Cargando análisis de ingresos',
                    lambda: render_entry_analysis_tab(data)
                )
            
            with tab3:
                show_loading_progress(
                    '📉 Cargando análisis de cierres',
                    lambda: render_closing_analysis_tab(data)
                )
            
            with tab4:
                show_loading_progress(
                    '👥 Cargando reporte por evaluador',
                    lambda: render_evaluator_report_tab(data)
                )
            
            with tab5:
                show_loading_progress(
                    '📋 Cargando reporte de asignaciones',
                    lambda: render_assignment_report_tab(data)
                )
            
            with tab6:
                show_loading_progress(
                    '🏆 Cargando ranking de expedientes',
                    lambda: ranking_report.render_ranking_report_tab(
                        data, 
                        selected_module, 
                        data_loader.get_rankings_collection()
                    )
                )

    except Exception as e:
        st.error(f"Error inesperado en la aplicación: {str(e)}")
        print(f"Error detallado: {str(e)}")

if __name__ == "__main__":
    main()
