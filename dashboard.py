import streamlit as st
from config.settings import MODULES
from src.services.data_loader import DataLoader
from tabs.pending_reports import render_pending_reports_tab
from tabs.entry_analysis import render_entry_analysis_tab
from tabs.closing_analysis import render_closing_analysis_tab
from tabs.evaluator_report import render_evaluator_report_tab
from tabs.assignment_report import render_assignment_report_tab
import tabs.ranking_report as ranking_report
from modules.spe.spe_module import SPEModule
from src.utils.database import get_google_credentials

st.set_page_config(layout="wide")

@st.cache_resource(show_spinner=False)
def get_data_loader():
    """Inicializa y retorna una instancia cacheada del DataLoader."""
    try:
        return DataLoader()
    except Exception as e:
        st.error(f"Error al inicializar DataLoader: {str(e)}")
        return None

def main():
    # Inicializar servicios
    data_loader = get_data_loader()
    
    # Obtener credenciales de Google
    try:
        google_credentials = get_google_credentials()
    except Exception as e:
        st.error(f"Error al obtener credenciales de Google: {str(e)}")
        return

    st.title("Gestión de Expedientes")

    # Mostrar última actualización de datos
    st.sidebar.markdown("### Última actualización")
    for module in MODULES:
        last_update = data_loader.get_latest_update(module)
        if last_update:
            st.sidebar.text(f"{MODULES[module]}: {last_update.strftime('%d/%m/%Y %H:%M')}")

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
        data = data_loader.load_module_data(selected_module)
        if data is None:
            st.error("No se encontraron datos para este módulo en la base de datos.")
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
            # Usar la misma conexión a MongoDB para el ranking
            ranking_report.render_ranking_report_tab(
                data, 
                selected_module, 
                data_loader.db.rankings
            )

if __name__ == "__main__":
    main()
