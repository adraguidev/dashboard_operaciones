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
from config.logging_config import logger
import gc
import psutil
import os

# Configuración de página
st.set_page_config(
    page_title="Gestión de Expedientes",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource(ttl=1800)  # 30 minutos
def get_data_loader():
    """Inicializa el DataLoader con configuración para la nube"""
    try:
        loader = DataLoader()
        # Timeouts más cortos para la nube
        loader.migraciones_db.command('ping', maxTimeMS=3000)
        loader.expedientes_db.command('ping', maxTimeMS=3000)
        return loader
    except Exception as e:
        logger.error(f"Error al inicializar DataLoader: {str(e)}")
        return None

def check_memory_usage():
    """Monitorea el uso de memoria de forma segura en la nube"""
    try:
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        # Log del uso de memoria
        logger.info(f"Uso de memoria actual: {memory_usage:.2f} MB")
        
        if memory_usage > 800:  # Umbral más bajo para la nube
            gc.collect()
            logger.warning(f"Alto uso de memoria: {memory_usage:.2f} MB - Limpiando cache")
            return True
        return False
    except Exception as e:
        logger.error(f"Error al verificar memoria: {str(e)}")
        return False

def main():
    try:
        # Inicializar servicios con manejo de memoria
        with st.spinner('Cargando datos...'):
            if check_memory_usage():
                st.warning("Alto uso de memoria detectado. Optimizando...")
            
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
                rankings_collection = data_loader.get_rankings_collection()
                ranking_report.render_ranking_report_tab(
                    data, 
                    selected_module, 
                    rankings_collection
                )

        # Monitorear memoria periódicamente
        if check_memory_usage():
            st.warning("Optimizando rendimiento...")

    except Exception as e:
        st.error(f"Error inesperado en la aplicación: {str(e)}")
        print(f"Error detallado: {str(e)}")

if __name__ == "__main__":
    main()
