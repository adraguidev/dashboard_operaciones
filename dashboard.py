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
        font-size: 0.9rem !important;
        color: #6c757d;
        font-weight: 600;
        margin-bottom: 0.5rem;
        padding-left: 0.5rem;
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
</style>
""", unsafe_allow_html=True)

# Función para mostrar el header con información del usuario
def show_header():
    st.markdown("""
        <div style="margin-bottom: 0.5rem;">
            <h1>📊 Gestión de Expedientes</h1>
        </div>
    """, unsafe_allow_html=True)

# Función para verificar última actualización (esta no se cachea para siempre verificar la DB)
def check_db_last_update(collection_name):
    """
    Verifica la última actualización en la base de datos.
    Esta función no se cachea para siempre obtener el último estado de la DB.
    """
    data_loader = st.session_state.data_loader
    return data_loader._get_collection_last_update(collection_name)

# Función cacheada para cargar datos del módulo
@st.cache_data(ttl=24*3600)
def load_module_data_cached(selected_module, collection_name, last_update_timestamp):
    """
    Carga y cachea los datos del módulo.
    El last_update_timestamp en los parámetros hace que se invalide el caché
    cuando hay una nueva actualización en la DB.
    """
    data_loader = st.session_state.data_loader
    data = data_loader.load_module_data(selected_module, last_update_timestamp)
    
    if data is not None:
        lima_tz = pytz.timezone('America/Lima')
        update_time = last_update_timestamp.astimezone(lima_tz) if last_update_timestamp else datetime.now(pytz.UTC).astimezone(lima_tz)
        return data, update_time
    return None, None

# Función para verificar la última actualización de la colección
@st.cache_data(ttl=24*3600)
def get_cached_last_update(collection_name):
    """
    Obtiene y cachea la fecha de última actualización de la colección
    """
    data_loader = st.session_state.data_loader
    return data_loader._get_collection_last_update(collection_name)

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

# Función para verificar y cargar datos del módulo
@st.cache_data(ttl=24*3600)
def get_module_data(selected_module, collection_name):
    """
    Función que maneja la lógica de verificación y carga de datos.
    Verifica la DB antes de usar el caché.
    """
    # Siempre verificar la última actualización en la DB
    last_update_in_db = check_db_last_update(collection_name)
    
    # Cargar datos (se usará caché si el last_update_in_db no ha cambiado)
    data, update_time = load_module_data_cached(selected_module, collection_name, last_update_in_db)
    
    if data is not None:
        return data, update_time, True
    return None, None, False

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
            with st.spinner('🔑 Verificando credenciales...'):
                google_credentials = get_google_credentials()
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
                options=list(MODULES.keys()),
                format_func=lambda x: MODULES[x],
                key="module_selector"
            )

            # Mostrar última actualización
            if 'update_time' in locals() and update_time:
                st.markdown(
                    f'<div class="update-info">📅 {update_time.strftime("%d/%m/%Y %H:%M")}</div>',
                    unsafe_allow_html=True
                )

        # Cargar datos según el módulo seleccionado
        if selected_module == 'SPE':
            if google_credentials is None:
                st.error("No se pueden cargar datos de SPE sin credenciales de Google.")
                return
            
            with st.spinner('🔄 Cargando módulo SPE...'):
                progress_bar = st.progress(0)
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)
                spe = SPEModule()
                st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                spe.render_module()
                st.markdown('</div>', unsafe_allow_html=True)
                progress_bar.empty()
        else:
            # Para otros módulos
            collection_name = MONGODB_COLLECTIONS.get(selected_module)
            if collection_name:
                with st.spinner(f'🔄 Cargando datos del módulo {MODULES[selected_module]}...'):
                    # Cargar datos con caché unificado
                    data, update_time, is_new_data = get_module_data(selected_module, collection_name)
                
                if data is None:
                    st.error("No se encontraron datos para este módulo en la base de datos.")
                    return

                # Mostrar última actualización con hora de Lima
                if update_time:
                    if is_new_data:
                        st.sidebar.success(f"Datos actualizados el: {update_time.strftime('%d/%m/%Y %H:%M')} (hora Lima)")
                    else:
                        st.sidebar.info(f"Usando datos del: {update_time.strftime('%d/%m/%Y %H:%M')} (hora Lima)")

            # Crear pestañas
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "Reporte de pendientes",
                "Ingreso de Expedientes",
                "Cierre de Expedientes",
                "Reporte por Evaluador",
                "Reporte de Asignaciones",
                "Ranking de Expedientes Trabajados"
            ])
            
            # Renderizar cada pestaña con efecto fade-in
            with tab1:
                with st.spinner('🔄 Cargando reporte de pendientes...'):
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    render_pending_reports_tab(data, selected_module)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with tab2:
                with st.spinner('🔄 Cargando análisis de ingresos...'):
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    render_entry_analysis_tab(data)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with tab3:
                with st.spinner('🔄 Cargando análisis de cierres...'):
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    render_closing_analysis_tab(data)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with tab4:
                with st.spinner('🔄 Cargando reporte por evaluador...'):
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    render_evaluator_report_tab(data)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with tab5:
                with st.spinner('🔄 Cargando reporte de asignaciones...'):
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    render_assignment_report_tab(data)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            with tab6:
                with st.spinner('🔄 Cargando ranking de expedientes...'):
                    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
                    rankings_collection = data_loader.get_rankings_collection()
                    ranking_report.render_ranking_report_tab(
                        data, 
                        selected_module, 
                        rankings_collection
                    )
                    st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Error inesperado en la aplicación: {str(e)}")
        print(f"Error detallado: {str(e)}")

if __name__ == "__main__":
    main()
