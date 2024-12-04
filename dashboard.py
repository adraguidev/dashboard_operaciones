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

    # Selección de módulo
    selected_module = st.sidebar.radio(
        "Selecciona un módulo",
        options=list(MODULES.keys()),
        format_func=lambda x: MODULES[x]
    )

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
