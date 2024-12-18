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
import time
from datetime import datetime, timedelta
import pytz
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import numpy as np
import pandas as pd

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
    }
    
    section[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #FF4B4B !important;
        color: white !important;
    }
    
    /* Estilo para los submódulos */
    .submenu {
        margin-left: 0.5rem !important;
        margin-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        border-left: 2px solid #e9ecef !important;
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
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] ~ section[data-testid="stContent"] {
        margin-left: 0 !important;
        width: 100% !important;
        transition: margin 0.3s, width 0.3s !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="true"] ~ section[data-testid="stContent"] {
        margin-left: 220px !important;
        width: calc(100% - 220px) !important;
        transition: margin 0.3s, width 0.3s !important;
    }
    
    /* Estilos para las pestañas */
    .stTabs {
        background: transparent;
        padding: 0;
        box-shadow: none;
        margin-top: 0.5rem;
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
        transition: all 0.2s;
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
    }
    
    /* Estilo para los botones dentro de las pestañas */
    .stTabs button {
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    .stTabs button[kind="primary"] {
        background: linear-gradient(90deg, #FF4B4B 0%, #ff6b6b 100%);
        border: none;
        color: white;
        box-shadow: 0 2px 4px rgba(255,75,75,0.2);
    }
    
    .stTabs button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(255,75,75,0.3);
    }
    
    /* Botón de colapso del sidebar */
    button[data-testid="collapsedControl"] {
        display: block !important;
        position: fixed !important;
        top: 1rem !important;
        left: 1rem !important;
        background-color: white !important;
        border-radius: 4px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1) !important;
        z-index: 999 !important;
        height: 2.5rem !important;
        width: 2.5rem !important;
        padding: 0.5rem !important;
        transition: all 0.2s !important;
        border: 1px solid #dee2e6 !important;
    }
    
    button[data-testid="collapsedControl"]:hover {
        background-color: #f8f9fa !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
    }
    
    /* Estilos globales */
    :root {
        --primary-color: #FF4B4B;
        --primary-color-hover: #ff6b6b;
        --background-color: #ffffff;
        --sidebar-color: #f8f9fa;
        --text-color: #1f1f1f;
        --border-radius: 0.5rem;
        --transition-speed: 0.2s;
    }
    
    /* Fondo principal */
    .stApp {
        background-color: var(--background-color);
    }
    
    /* Estilos para el sidebar */
    section[data-testid="stSidebar"] {
        background-color: var(--sidebar-color);
        border-right: 1px solid rgba(0,0,0,0.1);
        box-shadow: 2px 0 5px rgba(0,0,0,0.05);
    }
    
    /* Contenedor principal */
    section[data-testid="stContent"] {
        padding: 1rem !important;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    /* Estilos para las pestañas */
    .stTabs {
        background: transparent;
        padding: 0;
        box-shadow: none;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        background-color: transparent;
        padding: 0;
        margin-bottom: 0;
        border-bottom: 2px solid #f1f1f1;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        background-color: transparent;
        border-radius: 4px 4px 0 0;
        color: #6c757d;
        font-size: 0.9rem;
        font-weight: 500;
        border: none;
        padding: 0 1.5rem;
        margin-right: 0.5rem;
        transition: all 0.2s;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #fff3f3;
        color: var(--primary-color);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, var(--primary-color) 0%, var(--primary-color-hover) 100%) !important;
        color: white !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 4px rgba(255,75,75,0.2) !important;
    }
    
    /* Contenido de las pestañas */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 1.5rem 0;
        background-color: transparent;
    }
    
    /* Estilos para cards */
    .stCard {
        background-color: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    .stCard:hover {
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para métricas */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 1.5rem;
        border-radius: var(--border-radius);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    [data-testid="stMetric"]:hover {
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para dataframes */
    .stDataFrame {
        background-color: white;
        padding: 1rem;
        border-radius: var(--border-radius);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    .stDataFrame:hover {
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para expanders */
    .streamlit-expanderHeader {
        background-color: white;
        border: 1px solid #f1f1f1 !important;
        border-radius: var(--border-radius) !important;
        transition: all 0.2s;
    }
    
    .streamlit-expanderHeader:hover {
        border-color: #e9ecef !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Estilos para headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color);
        font-weight: 600;
    }
    
    h1 {
        font-size: 1.75rem !important;
        margin-bottom: 1rem !important;
    }
    
    h2 {
        font-size: 1.5rem !important;
        margin-bottom: 1.5rem !important;
    }
    
    h3 {
        font-size: 1.25rem !important;
        margin-bottom: 1rem !important;
    }
    
    /* Ajustes para el contenedor principal */
    section[data-testid="stContent"] {
        padding: 1rem !important;
        max-width: 1400px;
        margin: 0 auto;
    }
    
    /* Eliminar líneas divisorias innecesarias */
    .main-nav, hr, .stMarkdown hr {
        display: none !important;
    }
    
    /* Ajustes para el sidebar */
    section[data-testid="stSidebar"] > div {
        padding-top: 1.5rem !important;
        background: linear-gradient(to bottom, var(--sidebar-color) 0%, rgba(248,249,250,0.97) 100%);
    }
    
    /* Ajustes para los radio buttons en el submenu */
    .submenu {
        margin-left: 0.5rem !important;
        padding-left: 0.5rem !important;
        border-left: 2px solid rgba(255,75,75,0.1) !important;
    }
    
    .submenu .stRadio > div {
        background: transparent !important;
        padding: 0 !important;
    }
    
    .submenu .stRadio label {
        background: rgba(255,255,255,0.8) !important;
        border: 1px solid #f1f1f1;
        margin-bottom: 0.2rem !important;
    }
    
    .submenu .stRadio label:hover {
        background: white !important;
        border-color: var(--primary-color);
    }
    
    /* Ajustes para los contenedores de datos */
    [data-testid="stMetric"], .stDataFrame, .streamlit-expanderHeader {
        background: rgba(255,255,255,0.8);
        border: 1px solid #f1f1f1;
        transition: all 0.2s;
    }
    
    [data-testid="stMetric"]:hover, .stDataFrame:hover, .streamlit-expanderHeader:hover {
        background: white;
        border-color: #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* Ajustes para el primer botón del sidebar */
    section[data-testid="stSidebar"] button:first-of-type {
        margin-top: 0 !important;
    }
    
    /* Mejoras para las pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        white-space: nowrap;
        transition: all 200ms ease-in-out;
        padding: 0 1.5rem;
        margin-right: -1px;
        color: #666;
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-bottom: none;
        border-radius: 4px 4px 0 0;
        position: relative;
        z-index: 1;
    }

    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #FF4B4B !important;
        border-bottom: 2px solid #FF4B4B !important;
        z-index: 2;
    }

    .stTabs [data-baseweb="tab-panel"] {
        padding: 1.5rem 0.5rem;
        border-top: 1px solid #dee2e6;
        margin-top: -1px;
    }

    /* Animación de carga */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stTabs [data-baseweb="tab-panel"] > div {
        animation: fadeIn 0.3s ease-in-out;
    }
</style>
""", unsafe_allow_html=True)

# Función para mostrar el header con información del usuario
def show_header():
    st.markdown("""
        <div style="margin-bottom: 0.5rem;">
            <h1>📊 Gestión de Expedientes</h1>
        </div>
    """, unsafe_allow_html=True)

# Función para verificar última actualización (cacheada por 5 minutos)
@st.cache_data(ttl=300)
def get_current_time():
    """
    Retorna la hora actual en la zona horaria de Lima.
    """
    lima_tz = pytz.timezone('America/Lima')
    return datetime.now(pytz.UTC).astimezone(lima_tz)

# Función para generar hash de datos
def generate_data_hash(data):
    """
    Genera un hash único para los datos.
    Esto nos ayuda a detectar cambios reales en los datos.
    """
    import hashlib
    import json
    
    # Convertir DataFrame a string para hashear
    if hasattr(data, 'to_json'):
        data_str = data.to_json()
    else:
        data_str = json.dumps(str(data))
    
    return hashlib.md5(data_str.encode()).hexdigest()

# Función cacheada para cargar datos del módulo y su timestamp
@st.cache_data(ttl=None, persist="disk")  # Cache permanente y persistente en disco
def load_module_data_with_timestamp(selected_module):
    """
    Carga y cachea los datos del módulo junto con su timestamp.
    El caché persiste en disco y solo se invalida manualmente desde el panel de control.
    """
    # Verificar si hay una actualización forzada desde el panel de control
    if st.session_state.get('force_refresh', False):
        st.cache_data.clear()
        st.session_state.force_refresh = False
    
    data_loader = st.session_state.data_loader
    data = data_loader.load_module_data(selected_module)
    
    if data is not None:
        update_time = get_current_time()
        data_hash = generate_data_hash(data)
        
        return {
            'data': data,
            'update_time': update_time,
            'data_hash': data_hash,
            'load_time': update_time
        }
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def prepare_common_data(df):
    """Preprocesar datos comunes para todas las pestañas con optimización agresiva"""
    try:
        if df is None or df.empty:
            return None

        # Crear una vista sin copiar datos
        processed_df = df.copy(deep=False)
        
        # Pre-calcular columnas de fecha para evitar múltiples selects
        date_cols = processed_df.select_dtypes(include=['datetime64']).columns.tolist()
        
        if date_cols:
            # Procesar fechas en chunks para mejor rendimiento
            chunk_size = max(1000, len(processed_df) // 4)  # Ajustar según cantidad de datos
            num_chunks = (len(processed_df) + chunk_size - 1) // chunk_size
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = []
                
                def process_date_chunk(chunk_df, cols):
                    result = {}
                    for col in cols:
                        result[col] = chunk_df[col].dt.strftime('%d/%m/%Y')
                    return result
                
                # Dividir en chunks y procesar en paralelo
                for i in range(num_chunks):
                    start_idx = i * chunk_size
                    end_idx = min((i + 1) * chunk_size, len(processed_df))
                    chunk = processed_df.iloc[start_idx:end_idx]
                    futures.append(executor.submit(process_date_chunk, chunk, date_cols))
                
                # Recolectar resultados
                formatted_dates = {}
                for i, future in enumerate(futures):
                    chunk_result = future.result()
                    start_idx = i * chunk_size
                    for col, values in chunk_result.items():
                        if col not in formatted_dates:
                            formatted_dates[col] = pd.Series(index=processed_df.index, dtype='object')
                        formatted_dates[col].iloc[start_idx:start_idx + len(values)] = values.values

                # Asignar resultados optimizadamente
                for col in date_cols:
                    processed_df[f"{col}_formatted"] = formatted_dates[col]

        # Optimizar tipos de datos de manera más eficiente
        object_cols = processed_df.select_dtypes(include=['object']).columns
        
        def optimize_column(col):
            unique_ratio = processed_df[col].nunique() / len(processed_df)
            if unique_ratio < 0.5:
                return col, pd.Categorical(processed_df[col])
            return col, processed_df[col]
        
        # Optimizar tipos en paralelo
        with ThreadPoolExecutor(max_workers=4) as executor:
            optimized_cols = dict(executor.map(
                optimize_column,
                [col for col in object_cols if col not in [f"{c}_formatted" for c in date_cols]]
            ))
        
        # Actualizar columnas optimizadas
        for col, optimized_series in optimized_cols.items():
            processed_df[col] = optimized_series

        return processed_df
    except Exception as e:
        st.error(f"Error en prepare_common_data: {str(e)}")
        return df

def get_module_data(selected_module, collection_name):
    """Función optimizada para manejo de caché y carga de datos"""
    cache_key = f"data_{selected_module}"
    cache_hash_key = f"{selected_module}_data_hash"
    
    # Verificar si los datos están en caché y son válidos
    if (cache_key in st.session_state and 
        st.session_state.get('last_module') == selected_module):
        cached_data = st.session_state[cache_key]
        return cached_data['original'], cached_data['update_time'], False

    # Cargar datos frescos
    try:
        cached_data = load_module_data_with_timestamp(selected_module)
        if cached_data is not None:
            current_hash = cached_data['data_hash']
            
            # Actualizar caché solo si los datos han cambiado
            if current_hash != st.session_state.get(cache_hash_key):
                st.session_state[cache_hash_key] = current_hash
                return cached_data['data'], cached_data['update_time'], True
            
            return cached_data['data'], cached_data['update_time'], False
    except Exception as e:
        st.error(f"Error cargando datos: {str(e)}")
    
    return None, None, False

# Alternativa sin cache_resource
if 'data_loader' not in st.session_state:
    try:
        with st.spinner('🔄 Inicializando conexión a la base de datos...'):
            st.session_state.data_loader = DataLoader()
    except Exception as e:
        st.error(f"Error al inicializar DataLoader: {str(e)}")
        st.session_state.data_loader = None

# Función para obtener la fecha y hora actual en Lima
def get_lima_datetime():
    lima_tz = pytz.timezone('America/Lima')
    return datetime.now(pytz.UTC).astimezone(lima_tz)

# Función helper para mostrar spinner con progress bar
def show_loading_progress(message, action, show_fade_in=True):
    """
    Muestra un spinner con barra de progreso mientras se ejecuta una acción.
    
    Args:
        message: Mensaje a mostrar durante la carga
        action: Función a ejecutar
        show_fade_in: Si se debe mostrar el efecto fade-in
    Returns:
        El resultado de la acción ejecutada
    """
    with st.spinner(f'{message}...'):
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
        
        if show_fade_in:
            st.markdown('<div class="fade-in">', unsafe_allow_html=True)
        
        result = action()
        
        if show_fade_in:
            st.markdown('</div>', unsafe_allow_html=True)
        
        progress_bar.empty()
        return result

def main():
    try:
        data_loader = st.session_state.data_loader
        if data_loader is None:
            st.error("No se pudo inicializar la conexión a la base de datos.")
            return

        # Inicializar estados del menú si no existen
        if 'menu_dashboard' not in st.session_state:
            st.session_state.menu_dashboard = True
        if 'menu_admin' not in st.session_state:
            st.session_state.menu_admin = False
        if 'selected_module' not in st.session_state:
            st.session_state.selected_module = list(MODULES.keys())[0]
        if 'active_tab' not in st.session_state:
            st.session_state.active_tab = 0

        # Contenedor para el sidebar con estilo
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
                    st.session_state.selected_module = selected_module
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                selected_module = st.session_state.selected_module
            
            # Menú Admin
            if st.button("⚙️ Admin", key="btn_admin", use_container_width=True):
                st.session_state.menu_admin = True
                st.session_state.menu_dashboard = False
                st.switch_page("pages/1_admin.py")
            
            # Mostrar última actualización si está disponible
            if 'update_time' in locals():
                st.markdown(
                    f'<div class="update-info">📅 {update_time.strftime("%d/%m/%Y %H:%M")}</div>',
                    unsafe_allow_html=True
                )

        # Inicializar la fecha de datos actual en session_state si no existe
        if 'current_data_date' not in st.session_state:
            st.session_state.current_data_date = None

        # Obtener credenciales de Google
        try:
            google_credentials = get_google_credentials()
        except Exception as e:
            st.warning(f"No se pudieron obtener las credenciales de Google. SPE podría no funcionar correctamente.")
            google_credentials = None

        # Mostrar header
        show_header()

        # Cargar datos según el módulo seleccionado
        if selected_module == 'SPE':
            if google_credentials is None:
                st.error("No se pueden cargar datos de SPE sin credenciales de Google.")
                return
            
            spe = SPEModule()
            spe.render_module()
            update_time = get_current_time()
            
        else:
            # Para otros módulos
            collection_name = MONGODB_COLLECTIONS.get(selected_module)
            if collection_name:
                cache_key = f"data_{selected_module}"
                
                # Optimizar la lógica de carga
                if (cache_key not in st.session_state or 
                    st.session_state.get('last_module') != selected_module):
                    
                    with st.spinner(f'Cargando datos de {MODULES[selected_module]}...'):
                        data, update_time, needs_processing = get_module_data(selected_module, collection_name)
                        
                        if data is None:
                            st.error("No se encontraron datos para este módulo.")
                            return
                        
                        # Procesar datos solo si es necesario
                        if needs_processing:
                            processed_data = prepare_common_data(data)
                        else:
                            processed_data = st.session_state[cache_key].get('processed', None)
                            if processed_data is None:
                                processed_data = prepare_common_data(data)
                        
                        # Actualizar caché
                        st.session_state[cache_key] = {
                            'original': data,
                            'processed': processed_data,
                            'update_time': update_time
                        }
                        st.session_state['last_module'] = selected_module
                
                # Usar datos cacheados
                cached_data = st.session_state[cache_key]
                data = cached_data['original']
                processed_data = cached_data['processed']
                update_time = cached_data['update_time']

                # Limpiar caché antiguo de forma más eficiente
                if st.session_state.get('last_module') != selected_module:
                    old_module = st.session_state.get('last_module')
                    if old_module:
                        old_keys = [k for k in st.session_state.keys() 
                                   if k.startswith(f"data_{old_module}") or 
                                      k.startswith(f"tab_{old_module}_")]
                        for k in old_keys:
                            del st.session_state[k]

                # Definir las pestañas y sus funciones correspondientes
                tabs_config = [
                    ("Reporte de pendientes", render_pending_reports_tab, [data, selected_module]),
                    ("Ingreso de Expedientes", render_entry_analysis_tab, [data]),
                    ("Cierre de Expedientes", render_closing_analysis_tab, [data]),
                    ("Reporte por Evaluador", render_evaluator_report_tab, [data]),
                    ("Reporte de Asignaciones", render_assignment_report_tab, [data]),
                    ("Ranking de Expedientes Trabajados", ranking_report.render_ranking_report_tab, [data, selected_module, data_loader.get_rankings_collection()])
                ]

                # Crear pestañas usando st.tabs
                tabs = st.tabs([name for name, _, _ in tabs_config])

                # Renderizar contenido de las pestañas
                for i, tab in enumerate(tabs):
                    with tab:
                        # Usar el cache_key específico para cada pestaña
                        tab_cache_key = f"tab_{selected_module}_{i}"
                        
                        # Si es la primera vez que se carga esta pestaña o si los datos han cambiado
                        if tab_cache_key not in st.session_state or st.session_state.get('last_module') != selected_module:
                            with st.spinner(f'Cargando {tabs_config[i][0]}...'):
                                # Obtener la función y argumentos de la configuración
                                _, render_func, args = tabs_config[i]
                                render_func(*args)
                                st.session_state[tab_cache_key] = True
                        else:
                            # Obtener la función y argumentos de la configuración
                            _, render_func, args = tabs_config[i]
                            render_func(*args)

    except Exception as e:
        st.error(f"Error inesperado en la aplicación: {str(e)}")
        print(f"Error detallado: {str(e)}")

if __name__ == "__main__":
    main()
