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
        # Liberar memoria antes de crear nueva instancia
        import gc
        gc.collect()
        
        loader = DataLoader()
        # Verificar conexiones con timeout
        loader.migraciones_db.command('ping', maxTimeMS=5000)
        loader.expedientes_db.command('ping', maxTimeMS=5000)
        return loader
    except Exception as e:
        st.error(f"Error al inicializar DataLoader: {str(e)}")
        return None

def main():
    try:
        # Configurar límite de memoria para streamlit
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024 * 2, -1))  # 2GB limit
        
        # Inicializar servicios con manejo de memoria
        with st.spinner('Cargando datos...'):
            data_loader = get_data_loader()
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

        # Selección de módulo (directamente, sin mostrar últimas actualizaciones)
        selected_module = st.sidebar.radio(
            "Selecciona un módulo",
            options=list(MODULES.keys()),
            format_func=lambda x: MODULES[x]
        )

        # Cargar datos según el módulo seleccionado
        if selected_module == 'SPE':
            if google_credentials is None:
                st.error("No se pueden cargar datos de SPE sin credenciales de Google.")
                return
            with st.spinner('Cargando módulo SPE...'):
                spe = SPEModule()
                spe.render_module()
        else:
            with st.spinner('Cargando datos del módulo...'):
                try:
                    # Limpiar caché si hay error previo
                    if st.session_state.get('data_error'):
                        st.cache_data.clear()
                        st.session_state.data_error = False
                    
                    data = data_loader.load_module_data(selected_module)
                    if data is None:
                        st.error("No se encontraron datos para este módulo en la base de datos.")
                        return
                    
                    # Verificar tamaño de datos
                    data_size = data.memory_usage(deep=True).sum() / 1024**2  # MB
                    if data_size > 500:  # Si datos superan 500MB
                        st.warning(f"El conjunto de datos es grande ({data_size:.1f}MB). Puede afectar el rendimiento.")
                
                except Exception as e:
                    st.session_state.data_error = True
                    st.error(f"Error al cargar datos del módulo: {str(e)}")
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
                rankings_collection = data_loader.get_rankings_collection()
                ranking_report.render_ranking_report_tab(
                    data, 
                    selected_module, 
                    rankings_collection
                )

    except Exception as e:
        st.error(f"Error inesperado en la aplicación: {str(e)}")
        import traceback
        st.error(f"Error detallado: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
