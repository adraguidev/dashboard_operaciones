import streamlit as st
import pymongo
from config.settings import MODULES
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
    with st.sidebar:
        st.markdown("""
        <style>
        .module-container {
            background-color: rgba(49, 51, 63, 0.2);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
        }
        .module-header {
            color: #ffffff;
            font-size: 1.2em;
            margin-bottom: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 5px;
        }
        .stButton > button {
            background-color: transparent;
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.1);
            width: 100%;
            padding: 10px;
            margin: 5px 0;
            text-align: left;
        }
        .stButton > button:hover {
            border-color: #00acee;
            background-color: rgba(0, 172, 238, 0.1);
        }
        </style>
        """, unsafe_allow_html=True)

        st.title("Dashboard")
        st.markdown("---")
        
        # Agrupar módulos por categoría
        module_groups = {
            "Módulos Principales": {
                "CCM": "📊 Control de Calidad Migratoria",
                "PRR": "📈 Prórroga de Residencia",
                "CCM-ESP": "📉 CCM Especial"
            },
            "Módulos Especiales": {
                "CCM-LEY": "📋 CCM Legal",
                "SOL": "📂 Solicitudes",
                "SPE": "💼 Sistema Pendientes"
            }
        }

        selected_module = None
        
        for group_name, modules in module_groups.items():
            st.markdown(f"""
            <div class="module-container">
                <div class="module-header">{group_name}</div>
            </div>
            """, unsafe_allow_html=True)
            
            for module_key, module_label in modules.items():
                if st.button(
                    module_label,
                    key=f"btn_{module_key}",
                    help=f"Ver dashboard de {module_label}",
                    use_container_width=True
                ):
                    selected_module = module_key
        
        st.markdown("---")
        with st.expander("ℹ️ Ayuda"):
            st.markdown("""
            - Selecciona un módulo para ver sus datos
            - Los datos se actualizan cada hora
            - Para más información, contacta a soporte
            """)
        
        return selected_module

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
        if selected_module == 'SPE':
            spe = SPEModule()
            spe.render_module()
        else:
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
