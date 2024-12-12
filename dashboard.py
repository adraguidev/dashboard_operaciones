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

# Configuración de página
st.set_page_config(
    page_title="Gestión de Expedientes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Alternativa sin cache_resource
if 'data_loader' not in st.session_state:
    try:
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

        # Obtener credenciales de Google
        try:
            google_credentials = get_google_credentials()
        except Exception as e:
            st.warning(f"No se pudieron obtener las credenciales de Google. SPE podría no funcionar correctamente.")
            google_credentials = None

        st.title("Gestión de Expedientes")

        # Selección de módulo
        selected_module = st.sidebar.radio(
            "Selecciona un módulo",
            options=list(MODULES.keys()),
            format_func=lambda x: MODULES[x]
        )

        # Cargar datos según el módulo seleccionado
        if selected_module == 'SPE':
            # SPE siempre se carga fresco
            if google_credentials is None:
                st.error("No se pueden cargar datos de SPE sin credenciales de Google.")
                return
            with st.spinner('Cargando módulo SPE...'):
                spe = SPEModule()
                spe.render_module()
        else:
            # Para otros módulos, verificar última actualización
            collection_name = MONGODB_COLLECTIONS.get(selected_module)
            if collection_name:
                last_update = data_loader._get_collection_last_update(collection_name)
                
                with st.spinner('Cargando datos del módulo...'):
                    data = data_loader.load_module_data(selected_module, last_update)
                    if data is None:
                        st.error("No se encontraron datos para este módulo en la base de datos.")
                        return

                # Mostrar última actualización
                if last_update:
                    st.sidebar.info(f"Última actualización: {last_update.strftime('%d/%m/%Y %H:%M')}")

            # Crear pestañas
            tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
                "Reporte de pendientes",
                "Ingreso de Expedientes",
                "Cierre de Expedientes",
                "Reporte por Evaluador",
                "Reporte de Asignaciones",
                "Ranking de Expedientes Trabajados"
            ])
            
            # Renderizar cada pestaña
            with tab1:
                render_pending_reports_tab(data, selected_module)
            
            with tab2:
                render_entry_analysis_tab(data)
            
            with tab3:
                render_closing_analysis_tab(data)
            
            with tab4:
                render_evaluator_report_tab(data)
            
            with tab5:
                render_assignment_report_tab(data)
            
            with tab6:
                rankings_collection = data_loader.get_rankings_collection()
                ranking_report.render_ranking_report_tab(
                    data, 
                    selected_module, 
                    rankings_collection
                )

    except Exception as e:
        st.error(f"Error inesperado en la aplicación: {str(e)}")
        print(f"Error detallado: {str(e)}")

if __name__ == "__main__":
    main()
