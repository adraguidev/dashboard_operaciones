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

# Configuración de página
st.set_page_config(
    page_title="Gestión de Expedientes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource(show_spinner=False, ttl=3600)
def get_data_loader():
    """Inicializa y retorna una instancia cacheada del DataLoader."""
    try:
        loader = DataLoader()
        # Verificar conexión con timeout
        loader.migraciones_db.command('ping', maxTimeMS=5000)
        loader.expedientes_db.command('ping', maxTimeMS=5000)
        return loader
    except Exception as e:
        st.error(f"Error al inicializar DataLoader: {str(e)}")
        return None

def main():
    try:
        # Inicializar servicios con manejo de memoria y errores mejorado
        with st.spinner('Cargando datos...'):
            data_loader = get_data_loader()
            if data_loader is None:
                st.error("No se pudo inicializar la conexión a la base de datos.")
                return

        # Agregar manejo de errores para credenciales de Google
        google_credentials = None
        try:
            google_credentials = get_google_credentials()
        except Exception as e:
            st.warning("No se pudieron obtener las credenciales de Google. SPE podría no funcionar correctamente.")

        st.title("Gestión de Expedientes")

        # Selección de módulo con manejo de estado
        selected_module = st.sidebar.radio(
            "Selecciona un módulo",
            options=list(MODULES.keys()),
            format_func=lambda x: MODULES[x],
            key='module_selector'  # Agregar key para mejor manejo de estado
        )

        # Cargar datos con manejo de memoria y errores mejorado
        if selected_module == 'SPE':
            if google_credentials is None:
                st.error("No se pueden cargar datos de SPE sin credenciales de Google.")
                return
            
            try:
                with st.spinner('Cargando módulo SPE...'):
                    spe = SPEModule()
                    spe.render_module()
            except Exception as e:
                st.error(f"Error al cargar módulo SPE: {str(e)}")
                print(f"Error detallado SPE: {str(e)}")
                return
        else:
            try:
                with st.spinner(f'Cargando datos del módulo {selected_module}...'):
                    data = data_loader.load_module_data(selected_module)
                    if data is None:
                        st.error(f"No se encontraron datos para el módulo {selected_module}.")
                        return

                    # Verificar integridad de datos críticos
                    required_columns = ['NumeroTramite', 'FechaExpendiente', 'Evaluado']
                    missing_columns = [col for col in required_columns if col not in data.columns]
                    if missing_columns:
                        st.error(f"Faltan columnas requeridas: {', '.join(missing_columns)}")
                        return

                    # Renderizar pestañas con manejo de errores individual
                    tabs = st.tabs([
                        "Reporte de pendientes",
                        "Ingreso de Expedientes",
                        "Cierre de Expedientes",
                        "Reporte por Evaluador",
                        "Reporte de Asignaciones",
                        "Ranking de Expedientes Trabajados"
                    ])

                    for i, (tab, render_func) in enumerate([
                        (tabs[0], lambda: render_pending_reports_tab(data, selected_module)),
                        (tabs[1], lambda: render_entry_analysis_tab(data)),
                        (tabs[2], lambda: render_closing_analysis_tab(data)),
                        (tabs[3], lambda: render_evaluator_report_tab(data)),
                        (tabs[4], lambda: render_assignment_report_tab(data)),
                        (tabs[5], lambda: ranking_report.render_ranking_report_tab(
                            data, 
                            selected_module, 
                            data_loader.get_rankings_collection()
                        ))
                    ]):
                        try:
                            with tab:
                                render_func()
                        except Exception as e:
                            with tab:
                                st.error(f"Error al renderizar pestaña: {str(e)}")
                                print(f"Error detallado en pestaña {i}: {str(e)}")

            except Exception as e:
                st.error(f"Error al procesar datos del módulo {selected_module}: {str(e)}")
                print(f"Error detallado en procesamiento: {str(e)}")
                return

    except Exception as e:
        st.error(f"Error inesperado en la aplicación: {str(e)}")
        print(f"Error detallado: {str(e)}")

if __name__ == "__main__":
    main()
