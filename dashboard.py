import streamlit as st
import pymongo
from config.settings import MODULES_CONFIG
from data.data_loader import load_consolidated_cached, load_ccm_ley_data, load_spe_data
from tabs.pending_reports import render_pending_reports_tab
from tabs.entry_analysis import render_entry_analysis_tab
from tabs.closing_analysis import render_closing_analysis_tab
from tabs.evaluator_report import render_evaluator_report_tab
from tabs.assignment_report import render_assignment_report_tab
import tabs.ranking_report as ranking_report
from modules.spe.spe_module import SPEModule
from src.utils.database import get_google_credentials

st.set_page_config(layout="wide")

@st.cache_resource
def init_connection():
    return pymongo.MongoClient(st.secrets["connections"]["mongodb"]["uri"])

def render_sidebar():
    """Renderiza el sidebar con un diseño mejorado."""
    with st.sidebar:
        st.markdown("""
        <style>
        .sidebar-module {
            padding: 10px;
            margin: 5px 0;
            border-radius: 5px;
            border-left: 3px solid;
            background-color: rgba(255, 255, 255, 0.1);
            transition: all 0.3s;
        }
        .sidebar-module:hover {
            background-color: rgba(255, 255, 255, 0.2);
            transform: translateX(5px);
        }
        .module-icon {
            font-size: 1.2em;
            margin-right: 10px;
        }
        .module-title {
            font-size: 1.1em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .module-description {
            font-size: 0.9em;
            color: #888;
        }
        </style>
        """, unsafe_allow_html=True)

        st.title("📊 Dashboard")
        st.markdown("---")

        # Agrupar módulos por categoría
        module_categories = {
            "Principal": ["CCM", "PRR", "CCM-ESP"],
            "Especiales": ["CCM-LEY", "SOL", "SPE"]
        }

        selected_module = None
        
        for category, modules in module_categories.items():
            st.markdown(f"### {category}")
            
            for module in modules:
                config = MODULES_CONFIG[module]
                
                # Crear un contenedor clickeable para cada módulo
                module_html = f"""
                <div class="sidebar-module" style="border-left-color: {get_module_color(module)}">
                    <div class="module-title">
                        <span class="module-icon">{config.icon}</span>
                        {config.name}
                    </div>
                    <div class="module-description">
                        {get_module_description(module)}
                    </div>
                </div>
                """
                
                if st.button(module, key=f"btn_{module}"):
                    selected_module = module
                    return selected_module

        # Información adicional en el sidebar
        st.markdown("---")
        st.markdown("### 📌 Información")
        with st.expander("ℹ️ Ayuda"):
            st.markdown("""
            - Selecciona un módulo para ver sus datos
            - Los datos se actualizan cada hora
            - Para más información, contacta a soporte
            """)

        return selected_module

def get_module_color(module):
    """Retorna un color específico para cada módulo."""
    colors = {
        "CCM": "#FF6B6B",
        "PRR": "#4ECDC4",
        "CCM-ESP": "#45B7D1",
        "CCM-LEY": "#96CEB4",
        "SOL": "#FFEEAD",
        "SPE": "#D4A5A5"
    }
    return colors.get(module, "#888888")

def get_module_description(module):
    """Retorna una descripción corta para cada módulo."""
    descriptions = {
        "CCM": "Control de Calidad Migratoria",
        "PRR": "Prórroga de Residencia",
        "CCM-ESP": "Control de Calidad Especial",
        "CCM-LEY": "Control de Calidad Legal",
        "SOL": "Solicitudes",
        "SPE": "Sistema de Pendientes de Evaluación"
    }
    return descriptions.get(module, "")

def main():
    # Inicializar conexiones
    client = init_connection()
    db = client.expedientes_db
    collection = db.rankings
    
    # Obtener credenciales de Google
    try:
        google_credentials = get_google_credentials()
    except Exception as e:
        st.error(f"Error al obtener credenciales de Google: {str(e)}")
        return

    st.title("Gestión de Expedientes")

    # Renderizar sidebar y obtener módulo seleccionado
    selected_module = render_sidebar()

    if selected_module:
        # Cargar datos según el módulo seleccionado
        data = load_module_data(selected_module)
        if data is None:
            st.error("No se encontró el archivo consolidado para este módulo.")
            return

        # Crear pestañas
        tabs = st.tabs([
            "Reporte de pendientes",
            "Ingreso de Expedientes",
            "Cierre de Expedientes",
            "Reporte por Evaluador",
            "Reporte de Asignaciones",
            "Ranking de Expedientes Trabajados"
        ])

        # Renderizar cada pestaña
        with tabs[0]:
            render_pending_reports_tab(data, selected_module)
        with tabs[1]:
            render_entry_analysis_tab(data)
        with tabs[2]:
            render_closing_analysis_tab(data)
        with tabs[3]:
            render_evaluator_report_tab(data)
        with tabs[4]:
            render_assignment_report_tab(data)
        with tabs[5]:
            ranking_report.render_ranking_report_tab(data, selected_module, collection)

def load_module_data(selected_module):
    if selected_module == 'CCM-LEY':
        return load_ccm_ley_data()
    elif selected_module == 'SPE':
        return load_spe_data()
    else:
        return load_consolidated_cached(selected_module)

if __name__ == "__main__":
    main()
