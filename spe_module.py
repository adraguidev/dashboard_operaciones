import pandas as pd
import plotly.express as px
from io import BytesIO
import streamlit as st
from google.oauth2 import service_account
import gspread
import pandas as pd
from src.utils.database import get_google_credentials

# Configuración de credenciales de Google Sheets
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

@st.cache_resource
def get_google_sheets_client():
    """Inicializar cliente de Google Sheets con caché."""
    credentials = get_google_credentials()
    return gspread.authorize(credentials)

def load_spe_data():
    """Cargar datos desde Google Sheets."""
    try:
        client = get_google_sheets_client()
        # Reemplazar con el ID de tu hoja de Google Sheets
        sheet = client.open_by_key('TU_ID_DE_HOJA').worksheet('NOMBRE_DE_HOJA')
        data = pd.DataFrame(sheet.get_all_records())
        return data
    except Exception as e:
        st.error(f"Error al cargar datos de Google Sheets: {str(e)}")
        return None

def render_spe_module():
    """Renderizar el módulo SPE."""
    st.title("Módulo SPE")
    
    # Cargar datos
    data = load_spe_data()
    
    if data is None:
        st.error("No se pudieron cargar los datos del módulo SPE.")
        return

    # Pestaña única de Reporte de Pendientes
    st.header("Reporte de Pendientes")

    # Filtrar registros con ETAPA_EVALUACION vacío o "INICIADA"
    pendientes = data[data['ETAPA_EVALUACION'].isin(["", "INICIADA"]) | data['ETAPA_EVALUACION'].isna()]

    if pendientes.empty:
        st.info("No se encontraron expedientes pendientes.")
    else:
        # Contar pendientes por evaluador
        pendientes_por_evaluador = pendientes.groupby('EVALASIGN').size().reset_index(name='Cantidad')
        pendientes_por_evaluador = pendientes_por_evaluador.sort_values(by='Cantidad', ascending=False)

        # Mostrar los resultados en una tabla
        st.subheader("Cantidad de Pendientes por Evaluador")
        st.dataframe(
            pendientes_por_evaluador,
            use_container_width=True
        )

        # Crear gráfico de barras
        st.subheader("Distribución de Pendientes por Evaluador")
        fig = px.bar(
            pendientes_por_evaluador,
            x='EVALASIGN',
            y='Cantidad',
            title="Pendientes por Evaluador",
            labels={'EVALASIGN': 'Evaluador', 'Cantidad': 'Número de Expedientes'},
            text='Cantidad'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

        # Botón para descargar los datos en Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pendientes_por_evaluador.to_excel(writer, index=False, sheet_name='Pendientes')
            # Agregar hoja con detalle de expedientes pendientes
            pendientes[['NumeroTramite', 'EVALASIGN', 'ETAPA_EVALUACION']].to_excel(
                writer, 
                index=False, 
                sheet_name='Detalle_Pendientes'
            )
        output.seek(0)

        st.download_button(
            label="Descargar Reporte de Pendientes",
            data=output,
            file_name="Pendientes_SPE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
