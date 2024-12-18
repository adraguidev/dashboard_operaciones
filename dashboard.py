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
from src.utils.styles import apply_global_styles
from src.utils.state_manager import StateManager
from src.utils.display_utils import show_loading_progress
import time
from datetime import datetime, timedelta
import pytz

# Inicializar el estado y los estilos
StateManager.init_session_state()
apply_global_styles()

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
        transition: all 0.3s ease !important;
    }
    
    section[data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(135deg, #FF4B4B 0%, #ff6b6b 100%) !important;
        color: white !important;
        transform: translateY(0) !important;
    }
    
    section[data-testid="stSidebar"] button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 8px rgba(255,75,75,0.2) !important;
    }
    
    /* Estilo para los submódulos */
    .submenu {
        margin-left: 0.5rem !important;
        margin-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        border-left: 2px solid #e9ecef !important;
        animation: slideIn 0.3s ease-out !important;
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-10px); }
        to { opacity: 1; transform: translateX(0); }
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
        animation: fadeIn 0.5s ease-out !important;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
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
        transition: margin 0.3s ease !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] ~ section[data-testid="stContent"] {
        margin-left: 0 !important;
        width: 100% !important;
        transition: margin 0.3s ease, width 0.3s ease !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="true"] ~ section[data-testid="stContent"] {
        margin-left: 220px !important;
        width: calc(100% - 220px) !important;
        transition: margin 0.3s ease, width 0.3s ease !important;
    }
    
    /* Estilos para las pestañas */
    .stTabs {
        background: transparent;
        padding: 0;
        box-shadow: none;
        margin-top: 0.5rem;
        animation: fadeIn 0.5s ease-out;
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
        transition: all 0.3s ease;
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
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Estilo para los botones dentro de las pestañas */
    .stTabs button {
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        font-weight: 500;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #FF4B4B 0%, #ff6b6b 100%);
        border: none;
        color: white;
        cursor: pointer;
    }
    
    .stTabs button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(255,75,75,0.2);
    }
    
    /* Estilo para los spinners de carga */
    .stSpinner {
        margin: 2rem auto;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    /* Estilo para mensajes de error y éxito */
    .stAlert {
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
        animation: slideUp 0.3s ease-out;
    }
    
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Estilo para tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
    }
    
    .tooltip .tooltiptext {
        visibility: hidden;
        background-color: #2c3e50;
        color: white;
        text-align: center;
        padding: 0.5rem 1rem;
        border-radius: 4px;
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

# Función principal
def main():
    # Inicializar el DataLoader
    data_loader = DataLoader()
    
    # Sidebar
    with st.sidebar:
        st.markdown('<h1 style="text-align: center; color: #FF4B4B; margin-bottom: 2rem;">Dashboard USM</h1>', unsafe_allow_html=True)
        
        # Selector de módulo
        selected_module = st.selectbox(
            "Seleccionar Módulo",
            options=list(MODULES.keys()),
            format_func=lambda x: MODULES[x],
            key='module_selector'
        )
        
        # Guardar el módulo seleccionado en el estado
        if selected_module != StateManager.get_state('current_module'):
            StateManager.set_state('current_module', selected_module)
            StateManager.clear_cache()  # Limpiar caché al cambiar de módulo
        
        # Mostrar última actualización
        if selected_module in MONGODB_COLLECTIONS:
            collection_name = MONGODB_COLLECTIONS[selected_module]
            last_update = data_loader.get_last_update_time(collection_name)
            if last_update:
                st.markdown(
                    f'<div class="update-info">Última actualización:<br>{last_update}</div>',
                    unsafe_allow_html=True
                )
        
        # Botón de actualización de datos
        with st.expander("🔄 Actualizar Datos"):
            password = st.text_input("Contraseña", type="password")
            if st.button("Actualizar"):
                with st.spinner("Actualizando datos..."):
                    if data_loader.force_data_refresh(password):
                        st.success("✅ Datos actualizados correctamente")
                    else:
                        st.error("❌ Error al actualizar los datos")
    
    # Contenido principal
    if selected_module == 'SPE':
        SPEModule().render()
    else:
        # Cargar datos con indicador de progreso
        with st.spinner(f"Cargando datos de {MODULES[selected_module]}..."):
            show_loading_progress(f"Cargando {MODULES[selected_module]}")
            data = data_loader.load_module_data(selected_module)
        
        if data is not None:
            tabs = st.tabs([
                "📊 Pendientes",
                "📈 Análisis de Ingresos",
                "📉 Análisis de Cierre",
                "👥 Reporte por Evaluador",
                "📋 Reporte de Asignación",
                "🏆 Ranking"
            ])
            
            with tabs[0]:
                render_pending_reports_tab(data)
            with tabs[1]:
                render_entry_analysis_tab(data)
            with tabs[2]:
                render_closing_analysis_tab(data)
            with tabs[3]:
                render_evaluator_report_tab(data)
            with tabs[4]:
                render_assignment_report_tab(data)
            with tabs[5]:
                ranking_report.render_ranking_tab(data_loader, selected_module)
        else:
            st.error(f"No se pudieron cargar los datos para {MODULES[selected_module]}")

if __name__ == "__main__":
    main()
