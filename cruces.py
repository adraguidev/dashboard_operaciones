import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.worksheet.table import Table, TableStyleInfo
from file_utils import confirmar_sobrescritura

# Configuración de rutas
carpeta_raiz = "C:/report_download/manejo_reportes/"
carpeta_descargas = "C:/report_download/descargas/"

archivos_asignaciones = {
    "CCM": f"{carpeta_raiz}/CCM/ASIGNACIONES.xlsx",
    "PRR": f"{carpeta_raiz}/PRR/ASIGNACIONES.xlsx",
    "CCM-ESP": f"{carpeta_raiz}/CCM/ASIGNACIONES.xlsx",
    "SOL": f"{carpeta_raiz}/SOL/ASIGNACIONES.xlsx"
}

consolidados = {
    "CCM": f"{carpeta_descargas}/CCM/Consolidado_CCM.xlsx",
    "PRR": f"{carpeta_descargas}/PRR/Consolidado_PRR.xlsx",
    "CCM-ESP": f"{carpeta_descargas}/CCM-ESP/Consolidado_CCM-ESP.xlsx",
    "SOL": f"{carpeta_descargas}/SOL/Consolidado_SOL.xlsx"
}

consolidados_filtrados = {
    "CCM": f"{carpeta_descargas}/CCM/Consolidado_Filtrado_CCM.xlsx",
    "PRR": f"{carpeta_descargas}/PRR/Consolidado_Filtrado_PRR.xlsx",
    "CCM-ESP": f"{carpeta_descargas}/CCM-ESP/Consolidado_Filtrado_CCM.xlsx",
}

hojas_evaluadores = {
    "CCM": "CONSOLIDADO_CCM_X_EVAL",
    "PRR": "CONSOLIDADO_PRR_X_EVAL",
    "CCM-ESP": "CONSOLIDADO_CCM_X_EVAL",
    "SOL": "CONSOLIDADO_SOL_X_EVAL"
}

def procesar_cruces_combinados():
    # Crear lista de archivos de salida que se generarán
    archivos_salida = {
        tipo: consolidado_path.replace(".xlsx", "_CRUZADO.xlsx")
        for tipo, consolidado_path in consolidados.items()
    }
    
    if not confirmar_sobrescritura(archivos_salida):
        print("Proceso de cruces combinados omitido.")
        return
        
    for tipo in consolidados.keys():
        try:
            consolidado_path = consolidados[tipo]
            asignaciones_path = archivos_asignaciones[tipo]
            consolidado_filtrado_path = consolidados_filtrados.get(tipo)
            hoja_evaluador = hojas_evaluadores[tipo]
            
            output_path = archivos_salida[tipo]
            print(f"Procesando cruces para {tipo}")

            if not os.path.exists(consolidado_path) or not os.path.exists(asignaciones_path):
                print(f"Archivo no encontrado: {consolidado_path if not os.path.exists(consolidado_path) else asignaciones_path}")
                continue

            df_consolidado = pd.read_excel(consolidado_path)

            if "NumeroTramite" not in df_consolidado.columns:
                raise ValueError(f"La columna 'NumeroTramite' no existe en el consolidado {tipo}.")

            df_asignaciones = pd.read_excel(asignaciones_path, sheet_name=hoja_evaluador)
            df_asignaciones.columns = df_asignaciones.columns.str.strip()

            if "EVALUADOR" not in df_asignaciones.columns or "EXPEDIENTE" not in df_asignaciones.columns:
                raise ValueError(f"Columnas necesarias no encontradas en {asignaciones_path}.")

            df_asignaciones["EXPEDIENTE"] = df_asignaciones["EXPEDIENTE"].astype(str)
            evaluador_dict = pd.Series(df_asignaciones["EVALUADOR"].values, index=df_asignaciones["EXPEDIENTE"]).to_dict()

            df_consolidado["EVALASIGN"] = df_consolidado.apply(lambda row: calcular_evalasign(row, evaluador_dict), axis=1)

            if tipo != "SOL" and consolidado_filtrado_path and os.path.exists(consolidado_filtrado_path):
                df_filtrado = pd.read_excel(consolidado_filtrado_path)
                df_filtrado.columns = df_filtrado.columns.str.strip()

                columnas_adicionales = ["ESTADO", "DESCRIPCION", "FECHA DE TRABAJO"]
                if not all(col in df_filtrado.columns for col in ["EXPEDIENTE"] + columnas_adicionales):
                    raise ValueError(f"Columnas necesarias no encontradas en {consolidado_filtrado_path}.")

                df_filtrado["EXPEDIENTE"] = df_filtrado["EXPEDIENTE"].astype(str)
                
                for col in columnas_adicionales:
                    if df_filtrado[col].dtype == 'object':
                        df_filtrado[col] = pd.Categorical(df_filtrado[col], ordered=False)

                sort_columns = ["EXPEDIENTE"]
                if "FECHA DE TRABAJO" in df_filtrado.columns:
                    df_filtrado["FECHA DE TRABAJO"] = pd.to_datetime(df_filtrado["FECHA DE TRABAJO"], errors='coerce')
                    sort_columns.append("FECHA DE TRABAJO")
                
                df_filtrado = df_filtrado.sort_values(sort_columns, ascending=[True, False])
                df_filtrado = df_filtrado.drop_duplicates(subset="EXPEDIENTE", keep="first")

                df_consolidado = pd.merge(
                    df_consolidado,
                    df_filtrado[["EXPEDIENTE"] + columnas_adicionales],
                    left_on="NumeroTramite",
                    right_on="EXPEDIENTE",
                    how="left"
                ).drop(columns=["EXPEDIENTE"], errors="ignore")

            guardar_como_tabla_nueva(output_path, df_consolidado, f"BASE_{tipo}")
            print(f"Archivo cruzado guardado en: {output_path}")

        except Exception as e:
            print(f"Error al procesar {tipo}: {e}")

def calcular_evalasign(row, evaluador_dict):
    numero_tramite = row.get("NumeroTramite")
    if isinstance(numero_tramite, str):
        if row["Evaluado"] == "NO":
            return evaluador_dict.get(numero_tramite, None)
        elif row["Evaluado"] == "SI" and row["Pre_Concluido"] == "SI":
            return row.get("OperadorPre", None)
    return None

def guardar_como_tabla_nueva(archivo, df, tabla_nombre):
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = tabla_nombre

        for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=1):
            for c_idx, value in enumerate(row, start=1):
                ws.cell(row=r_idx, column=c_idx, value=value)

        table_ref = f"A1:{chr(64 + df.shape[1])}{df.shape[0] + 1}"
        table = Table(displayName=tabla_nombre, ref=table_ref)
        style = TableStyleInfo(
            name="TableStyleMedium9", showFirstColumn=False,
            showLastColumn=False, showRowStripes=True, showColumnStripes=True
        )
        table.tableStyleInfo = style
        ws.add_table(table)

        wb.save(archivo)
        print(f"Nuevo archivo creado: {archivo}")
    except Exception as e:
        print(f"Error al guardar nuevo archivo: {e}")

if __name__ == "__main__":
    procesar_cruces_combinados()