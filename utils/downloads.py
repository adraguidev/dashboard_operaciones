from io import BytesIO
import pandas as pd

def download_table_as_excel(data, title):
    """
    Generar archivo Excel a partir de un DataFrame.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False, sheet_name=title[:31])
    output.seek(0)
    return output

def download_detailed_list(data, filters):
    """
    Generar archivo detallado basado en filtros aplicados.
    """
    # Filtrar los datos según los filtros proporcionados
    filtered_data = data
    for key, value in filters.items():
        if value:  # Si el filtro tiene valores
            if isinstance(value, list):
                filtered_data = filtered_data[filtered_data[key].isin(value)]
            else:
                filtered_data = filtered_data[filtered_data[key] == value]

    # Seleccionar las columnas para el detalle
    details = filtered_data[['NumeroTramite', 'FechaExpendiente', 'EVALASIGN']]
    
    # Generar el archivo Excel
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        details.to_excel(writer, index=False, sheet_name="Detalles Filtrados")
    output.seek(0)
    return output 