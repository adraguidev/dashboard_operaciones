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
    /* Eliminar todo el padding superior */
    .main > div:first-child {
        padding-top: 0 !important;
    }
    
    /* Reducir espacio del contenedor principal */
    .main .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Ajustar el título para que esté más arriba */
    h1 {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 1.5rem !important;
        line-height: 1.2 !important;
    }
    
    /* Optimizar sidebar */
    section[data-testid="stSidebar"] {
        width: 15rem !important;
        min-width: 15rem !important;
        background-color: #f8f9fa;
    }
    
    section[data-testid="stSidebar"] > div {
        padding: 0.5rem !important;
    }
    
    /* Estilo para el título de módulos */
    .sidebar-title {
        font-size: 1.5rem !important;
        color: #1f1f1f;
        font-weight: 600;
        margin-bottom: 1rem;
        padding-left: 0.5rem;
    }
    
    /* Estilo para el expander de actualización */
    .small-expander {
        font-size: 0.8rem !important;
        color: #6c757d;
        margin-top: auto;
    }
    
    /* Contenedor para empujar contenido al fondo */
    .sidebar-bottom {
        position: fixed;
        bottom: 0;
        left: 0;
        padding: 0.5rem;
        width: inherit;
        background: white;
        z-index: 1000;
    }
    
    /* Estilo para el botón discreto de actualización */
    .update-button {
        opacity: 0.3;
        transition: opacity 0.3s;
        cursor: pointer;
        position: fixed;
        bottom: 10px;
        left: 10px;
        font-size: 1.2rem;
    }
    
    .update-button:hover {
        opacity: 1;
    }
    
    /* Estilo para el expander de actualización */
    div[data-testid="stExpander"] {
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
    }
    
    /* Ocultar el header del expander */
    .streamlit-expanderHeader {
        display: none;
    }
    
    /* Ajustar radio buttons del sidebar */
    .stRadio > div {
        gap: 0.2rem !important;
        background-color: white;
        padding: 0.5rem;
        border-radius: 0.3rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    .stRadio > label {
        font-size: 0.85rem !important;
        padding: 0.2rem 0 !important;
    }
    
    /* Estilo para los radio buttons */
    .stRadio [data-testid="stMarkdownContainer"] > p {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Ajustar mensajes de info/success en sidebar */
    .sidebar .stAlert {
        padding: 0.2rem !important;
        margin: 0.3rem 0 !important;
    }
    
    .sidebar .stAlert > div {
        padding: 0.2rem 0.4rem !important;
        min-height: unset !important;
        font-size: 0.7rem !important;
    }
    
    /* Estilo para el mensaje de actualización */
    .update-info {
        font-size: 0.7rem !important;
        color: #6c757d;
        padding: 0.2rem 0.4rem;
        background-color: #e9ecef;
        border-radius: 0.2rem;
        margin-top: 0.3rem;
        display: inline-block;
    }
    
    /* Reducir espacio de spinners y progress bars */
    .stSpinner {
        margin: 0.3rem 0 !important;
    }
    
    .stProgress {
        margin: 0.2rem 0 !important;
    }
    
    /* Ajustar espacio entre elementos */
    .element-container {
        margin: 0.2rem 0 !important;
    }
    
    /* Animaciones y efectos */
    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }
    @keyframes fadeIn {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }
    
    /* Personalización de la barra de progreso */
    .stProgress > div > div > div > div {
        background-color: #FF4B4B;
    }
    
    /* Estilos para spinners y loaders */
    .loading-spinner {
        text-align: center;
        padding: 20px;
    }
    
    /* Mejoras visuales generales */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Estilo para el sidebar */
    .css-1d391kg {
        background-color: #ffffff;
        border-right: 1px solid #e9ecef;
        padding: 2rem 1rem;
    }
    
    /* Estilo para las tarjetas */
    .stCard {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Estilo para las pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem !important;
        background-color: white;
        padding: 0.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        flex-wrap: wrap;
        row-gap: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        white-space: nowrap;
        background-color: transparent;
        border-radius: 4px;
        color: #0f1116;
        font-size: 13px;
        padding: 0 1rem !important;
        min-width: fit-content;
        flex-grow: 1;
        flex-basis: auto;
        text-align: center;
        max-width: 200px;
    }
    
    /* Ajuste para pantallas pequeñas */
    @media screen and (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            font-size: 12px;
            padding: 0 0.5rem !important;
            height: 2.2rem;
        }
        
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.3rem !important;
        }
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255, 75, 75, 0.1);
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B !important;
        color: white !important;
        font-weight: 500;
    }
    
    /* Contenedor de pestañas para asegurar espaciado correcto */
    .stTabs {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* Ajuste para el contenido de las pestañas */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 1rem 0.5rem;
    }
    
    /* Estilo para los botones */
    .stButton>button {
        background-color: #FF4B4B;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.3rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stButton>button:hover {
        background-color: #ff3333;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Estilo para métricas */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #FF4B4B;
        font-weight: bold;
    }
    
    /* Estilo para selectbox */
    .stSelectbox [data-baseweb="select"] {
        border-radius: 0.3rem;
    }
    
    /* Estilo para dataframes */
    .dataframe {
        border: none !important;
        border-radius: 0.5rem;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .dataframe th {
        background-color: #f8f9fa;
        padding: 0.75rem !important;
        font-weight: 600;
    }
    
    .dataframe td {
        padding: 0.75rem !important;
    }
    
    /* Estilo para tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
    }
    
    .tooltip .tooltiptext {
        visibility: hidden;
        background-color: #333;
        color: white;
        text-align: center;
        padding: 5px;
        border-radius: 6px;
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
    
    /* Estilo para el botón discreto de actualización */
    .update-icon {
        position: fixed;
        bottom: 20px;
        left: 20px;
        opacity: 0.3;
        font-size: 0.9rem;
        z-index: 1000;
        background: none;
        border: none;
        cursor: pointer;
        padding: 5px;
        transition: opacity 0.3s;
    }
    
    .update-icon:hover {
        opacity: 1;
    }
    
    /* Estilo para el contenedor de actualización */
    .update-container {
        position: fixed;
        bottom: 60px;
        left: 10px;
        background: white;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        z-index: 999;
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
    with st.spinner(f'🔄 {message}...'):
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

def render_admin_panel(data_loader):
    """Renderiza el panel de control administrativo."""
    st.markdown("## ⚙️ Panel de Control")
    
    # Secciones del panel
    st.markdown("### 🔄 Gestión de Datos")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Actualización de Datos")
        if st.button("Actualizar Base de Datos", key="admin_update"):
            st.session_state.force_refresh = True
            if data_loader.force_data_refresh("Ka260314!"):
                st.success("✅ Datos actualizados correctamente")
                st.rerun()
    
        st.markdown("#### Monitoreo de Conexiones")
        if st.button("Verificar Estado de Conexiones"):
            try:
                data_loader.migraciones_db.command('ping')
                st.success("✅ Conexión a MongoDB activa")
            except Exception as e:
                st.error(f"❌ Error de conexión: {str(e)}")
    
    with col2:
        st.markdown("#### Estadísticas del Sistema")
        # Mostrar estadísticas de caché
        st.metric("Módulos en Caché", len(st.session_state))
        st.metric("Última Actualización", 
                 get_current_time().strftime("%d/%m/%Y %H:%M"))
    
    st.markdown("---")
    st.markdown("### 📊 Configuración de Visualización")
    
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### Módulos Visibles")
        # Permitir habilitar/deshabilitar módulos
        if 'visible_modules' not in st.session_state:
            st.session_state.visible_modules = list(MODULES.keys())
        
        for module in MODULES.keys():
            if st.checkbox(MODULES[module], 
                         value=module in st.session_state.visible_modules,
                         key=f"module_visibility_{module}"):
                if module not in st.session_state.visible_modules:
                    st.session_state.visible_modules.append(module)
            else:
                if module in st.session_state.visible_modules:
                    st.session_state.visible_modules.remove(module)
    
    with col4:
        st.markdown("#### Configuración de Caché")
        if st.button("Limpiar Caché"):
            st.cache_data.clear()
            st.success("✅ Caché limpiado correctamente")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 🔍 Diagnóstico del Sistema")
    
    # Mostrar logs y errores recientes
    with st.expander("Logs del Sistema"):
        st.code("""
        [INFO] Última conexión exitosa: {time}
        [INFO] Total de consultas realizadas: {queries}
        [INFO] Uso de memoria caché: {cache_size}MB
        """.format(
            time=get_current_time().strftime("%d/%m/%Y %H:%M"),
            queries=len(st.session_state),
            cache_size=round(len(str(st.session_state)) / 1024, 2)
        ))

def main():
    try:
        data_loader = st.session_state.data_loader
        if data_loader is None:
            st.error("No se pudo inicializar la conexión a la base de datos.")
            return

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

        # Contenedor para el sidebar con estilo
        with st.sidebar:
            st.markdown('<p class="sidebar-title">🎯 MÓDULOS</p>', unsafe_allow_html=True)
            
            # Selección de módulo con estilo compacto
            selected_module = st.radio(
                "",
                options=st.session_state.get('visible_modules', list(MODULES.keys())),
                format_func=lambda x: MODULES[x],
                key="module_selector"
            )

            # Mostrar última actualización si está disponible
            if 'update_time' in locals():
                st.markdown(
                    f'<div class="update-info">📅 {update_time.strftime("%d/%m/%Y %H:%M")}</div>',
                    unsafe_allow_html=True
                )
            
            # Espacio flexible para empujar el botón al fondo
            st.markdown('<div style="flex: 1;"></div>', unsafe_allow_html=True)
            
            # Botón discreto para Panel de Control al final del sidebar
            cols = st.columns([19, 1])
            with cols[1]:
                if st.button("⚙️", help="Panel de Control", key="admin_button"):
                    st.session_state.show_admin = not st.session_state.get('show_admin', False)
            
            # Si se activa el panel de control, pedir contraseña
            if st.session_state.get('show_admin', False):
                with st.container():
                    password = st.text_input("Contraseña", type="password", key="admin_password")
                    if password == "Ka260314!":
                        st.session_state.admin_authenticated = True
                    elif password:
                        st.error("Contraseña incorrecta")

        # Si está autenticado como admin y el panel está activo, mostrar el panel
        if st.session_state.get('admin_authenticated', False) and st.session_state.get('show_admin', False):
            render_admin_panel(data_loader)
            return

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
                    f'Cargando datos del módulo {MODULES[selected_module]}',
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
                    'Cargando reporte de pendientes',
                    lambda: render_pending_reports_tab(data, selected_module)
                )
            
            with tab2:
                show_loading_progress(
                    'Cargando análisis de ingresos',
                    lambda: render_entry_analysis_tab(data)
                )
            
            with tab3:
                show_loading_progress(
                    'Cargando análisis de cierres',
                    lambda: render_closing_analysis_tab(data)
                )
            
            with tab4:
                show_loading_progress(
                    'Cargando reporte por evaluador',
                    lambda: render_evaluator_report_tab(data)
                )
            
            with tab5:
                show_loading_progress(
                    'Cargando reporte de asignaciones',
                    lambda: render_assignment_report_tab(data)
                )
            
            with tab6:
                show_loading_progress(
                    'Cargando ranking de expedientes',
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
