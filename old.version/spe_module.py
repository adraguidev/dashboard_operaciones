import pandas as pd
import plotly.express as px
from io import BytesIO
import streamlit as st

def generate_spe_report(data):
    """
    Genera el reporte de pendientes para el módulo SPE y lo muestra en Streamlit.

    Args:
        data (pd.DataFrame): Datos cargados desde Google Sheets.
    """
    st.header("Reporte de Pendientes")

    # Filtrar registros con ETAPA_EVALUACION vacío o "INICIADA"
    pendientes = data[data['ETAPA_EVALUACION'].isin(["", "INICIADA"]) | data['ETAPA_EVALUACION'].isna()]

    if pendientes.empty:
        st.info("No se encontraron expedientes con ETAPA_EVALUACION en blanco o 'INICIADA'.")
    else:
        # Contar pendientes por evaluador
        pendientes_por_evaluador = pendientes.groupby('EVALASIGN').size().reset_index(name='Cantidad')
        pendientes_por_evaluador = pendientes_por_evaluador.sort_values(by='Cantidad', ascending=False)

        # Mostrar los resultados en una tabla
        st.subheader("Cantidad de Pendientes por Evaluador")
        st.dataframe(pendientes_por_evaluador)

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
        st.plotly_chart(fig)

        # Botón para descargar los datos en Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pendientes_por_evaluador.to_excel(writer, index=False, sheet_name='Pendientes')
        output.seek(0)

        st.download_button(
            label="Descargar Reporte de Pendientes",
            data=output,
            file_name="Pendientes_SPE.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
