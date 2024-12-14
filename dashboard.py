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
        gap: 2rem;
        background-color: white;
        padding: 0.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #0f1116;
        font-size: 14px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B !important;
        color: white !important;
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
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        st.title("📊 Gestión de Expedientes")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="stCard" style="text-align: right;">
            <h4>Estado del Sistema</h4>
            <p style="color: #00c853;">● En línea</p>
        </div>
        """, unsafe_allow_html=True)

# Función para verificar si necesitamos actualizar la data
@st.cache_data(ttl=24*3600)  # Cache por 24 horas
def check_data_update_needed(collection_name, current_data_date):
    """
    Verifica si necesitamos actualizar la data comparando la fecha actual con la última actualización
    """
    data_loader = st.session_state.data_loader
    last_update = data_loader._get_collection_last_update(collection_name)
    
    if last_update is None:
        return True
    
    if current_data_date is None:
        return True
        
    return last_update > current_data_date

# Función cacheada para cargar datos del módulo
@st.cache_data(ttl=24*3600)  # Cache por 24 horas
def load_cached_module_data(selected_module, current_data_date):
    data_loader = st.session_state.data_loader
    return data_loader.load_module_data(selected_module, current_data_date)

# Función cacheada para obtener última actualización
@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_cached_last_update(collection_name):
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
            st.markdown("""
            <div class="stCard">
                <h3>🎯 Navegación</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Selección de módulo
            selected_module = st.radio(
                "Selecciona un módulo",
                options=list(MODULES.keys()),
                format_func=lambda x: MODULES[x]
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
            # Para otros módulos, verificar si necesitamos actualizar
            collection_name = MONGODB_COLLECTIONS.get(selected_module)
            if collection_name:
                # Verificar si necesitamos actualizar la data
                update_needed = check_data_update_needed(collection_name, st.session_state.current_data_date)
                
                if update_needed:
                    with st.spinner(f'🔄 Cargando nuevos datos del módulo {MODULES[selected_module]}...'):
                        progress_bar = st.progress(0)
                        for i in range(100):
                            time.sleep(0.01)
                            progress_bar.progress(i + 1)
                        data = load_cached_module_data(selected_module, st.session_state.current_data_date)
                        if data is not None:
                            st.session_state.current_data_date = datetime.now()
                        progress_bar.empty()
                else:
                    data = load_cached_module_data(selected_module, st.session_state.current_data_date)
                
                if data is None:
                    st.error("No se encontraron datos para este módulo en la base de datos.")
                    return

                # Mostrar última actualización
                if st.session_state.current_data_date:
                    st.sidebar.info(f"Datos actualizados el: {st.session_state.current_data_date.strftime('%d/%m/%Y %H:%M')}")

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
