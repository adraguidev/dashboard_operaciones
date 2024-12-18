# Imports principales
import streamlit as st

# Configuración de página - DEBE SER LA PRIMERA LLAMADA A STREAMLIT
st.set_page_config(
    page_title="Dashboard de Operaciones",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Imports y configuración
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

# CSS personalizado
st.markdown("""
    <style>
    /* ... tu CSS existente ... */
    </style>
""", unsafe_allow_html=True)

# Funciones auxiliares
def show_header():
    st.markdown("""
        <div style="margin-bottom: 0.5rem;">
            <h1>📊 Gestión de Expedientes</h1>
        </div>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_current_time():
    lima_tz = pytz.timezone('America/Lima')
    return datetime.now(pytz.UTC).astimezone(lima_tz)

def main():
    # Inicializar DataLoader si no existe
    if 'data_loader' not in st.session_state:
        with st.spinner('Inicializando conexión a la base de datos...'):
            try:
                st.session_state.data_loader = DataLoader()
            except Exception as e:
                st.error(f"Error al inicializar DataLoader: {str(e)}")
                st.error("No se pudo inicializar la conexión a la base de datos.")
                return
    
    data_loader = st.session_state.data_loader
    
    # Inicializar estados del menú
    if 'menu_dashboard' not in st.session_state:
        st.session_state.menu_dashboard = True
    if 'menu_admin' not in st.session_state:
        st.session_state.menu_admin = False
    if 'selected_module' not in st.session_state:
        st.session_state.selected_module = list(MODULES.keys())[0]
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0
    
    # Cargar datos comunes
    common_data = data_loader.prepare_common_data()
    if not common_data:
        st.error("❌ No se pudieron cargar los datos. Por favor, intente más tarde.")
        return

    # Sidebar
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
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            selected_module = st.session_state.selected_module
        
        # Menú Admin
        if st.button("⚙️ Admin", key="btn_admin", use_container_width=True):
            st.session_state.menu_admin = True
            st.session_state.menu_dashboard = False
            st.switch_page("pages/1_admin.py")

    # Mostrar header
    show_header()

    # Renderizar contenido según el módulo seleccionado
    if selected_module in common_data:
        data = common_data[selected_module]
        
        # Definir pestañas
        tabs_config = [
            ("Reporte de pendientes", render_pending_reports_tab, [data, selected_module]),
            ("Ingreso de Expedientes", render_entry_analysis_tab, [data]),
            ("Cierre de Expedientes", render_closing_analysis_tab, [data]),
            ("Reporte por Evaluador", render_evaluator_report_tab, [data]),
            ("Reporte de Asignaciones", render_assignment_report_tab, [data]),
            ("Ranking de Expedientes Trabajados", ranking_report.render_ranking_report_tab, [data, selected_module, data_loader.get_rankings_collection()])
        ]
        
        # Crear pestañas
        tabs = st.tabs([name for name, _, _ in tabs_config])
        
        # Renderizar contenido de las pestañas
        for i, (tab, (_, render_func, args)) in enumerate(zip(tabs, tabs_config)):
            with tab:
                render_func(*args)

if __name__ == "__main__":
    main()
