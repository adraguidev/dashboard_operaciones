import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def load_google_sheet_data(json_keyfile, sheet_name, worksheet_name):
    """
    Conecta a un Google Sheet y retorna los datos como un DataFrame de pandas.

    Args:
        json_keyfile (str): Ruta al archivo de credenciales JSON.
        sheet_name (str): Nombre del Google Sheet.
        worksheet_name (str): Nombre de la hoja dentro del Google Sheet.

    Returns:
        pd.DataFrame: Datos de la hoja como DataFrame.
    """
    try:
        # Alcance para usar Google Sheets y Google Drive APIs
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
        client = gspread.authorize(credentials)
        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        records = worksheet.get_all_records()
        return pd.DataFrame(records)
    except Exception as e:
        raise RuntimeError(f"Error al cargar datos desde Google Sheets: {e}")
