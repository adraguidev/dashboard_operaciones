import pandas as pd
import os

# Ruta de la carpeta de entrada y archivo de salida
input_folder = r"\\172.27.230.89\produccion_evaluadores_sgin\ASIGNACIONES\ASIGNACION CAMPAÑA"
output_file = "consolidado_filtrado_ccm.xlsx"

# Lista de estados válidos
estados_validos = [
    "Notificado por observación de requisitos",
    "Proceso Sancionador - PAS MULTA",
    "Notificado por observación de requisitos y PAS MULTA",
    "Notificado por observación de requisitos y PIDE \"para verificación\"",
    "Notificado por observación de requisitos, PIDE \"para verificación\"  y PAS MULTA",
    "Notificado por datos biométricos",
    "Notificado por observación de requisitos y datos biométricos",
    "Notificado por otras observaciones",
    "Observados por PIDE \"para verificación\" o \"agotamiento de \"cuota\"",
    "Pendiente por PAS MULTA y PIDE",
    "Por Regularización Masiva (Duplicidad y Registro Masivo)",
    "Error en el SIM INM",
    "DNV Positivo o Alerta Restrictiva",
    "Pre Aprobado",
    "Pre Denegado",
    "Pre Desistido",
    "Pre Abandono",
    "Pre No Presentado",
    "INTERPOL (por lista no remitida)",
    "Otro tramite pendiente y PAS MULTA",
    "Otro tramite pendiente",
    "APROBADO",
    "DENEGADO",
    "ANULADO",
    "DESISTIDO",
    "ABANDONO",
    "NO PRESENTADO",
    "Pendiente (Por encauzamiento, etapas, etc)"
]

def normalizar_estado(estado):
    """Normaliza el estado eliminando espacios antes y después."""
    return estado.strip().upper() if isinstance(estado, str) else None

def extraer_relevante(df, archivo_origen):
    """Extrae las columnas EXPEDIENTE, ESTADO, DESCRIPCION y FECHA DE TRABAJO si existen."""
    df.columns = [col.strip().upper() for col in df.columns]
    columnas_necesarias = ["EXPEDIENTE", "ESTADO", "DESCRIPCION (OPCIONAL)", "DESCRIPCION", "FECHA DE TRABAJO"]
    columnas_presentes = [col for col in columnas_necesarias if col in df.columns]
    df_filtrado = df[columnas_presentes].copy()

    # Renombrar DESCRIPCION (OPCIONAL) a DESCRIPCION si está presente
    if "DESCRIPCION (OPCIONAL)" in df_filtrado:
        df_filtrado.rename(columns={"DESCRIPCION (OPCIONAL)": "DESCRIPCION"}, inplace=True)

    # Filtrar EXPEDIENTE que empieza con "LM"
    if "EXPEDIENTE" in df_filtrado:
        df_filtrado = df_filtrado[df_filtrado["EXPEDIENTE"].str.startswith("LM", na=False)]

    # Normalizar y filtrar ESTADO
    if "ESTADO" in df_filtrado:
        df_filtrado["ESTADO"] = df_filtrado["ESTADO"].apply(normalizar_estado)
        df_filtrado = df_filtrado[df_filtrado["ESTADO"].isin([estado.upper() for estado in estados_validos])]

    # Agregar columna de archivo origen al final
    df_filtrado["ARCHIVO_ORIGEN"] = archivo_origen

    return df_filtrado

def consolidar_archivos_filtrados(input_folder, output_file):
    # Lista para almacenar los datos filtrados
    datos_filtrados = []

    try:
        for archivo in os.listdir(input_folder):
            archivo_path = os.path.join(input_folder, archivo)
            
            # Ignorar archivos temporales y no Excel
            if os.path.isfile(archivo_path) and archivo.endswith((".xls", ".xlsx")) and not archivo.startswith("~$"):
                try:
                    # Intentar leer la hoja "ASIGNACION", si no existe usar la primera hoja
                    try:
                        df = pd.read_excel(archivo_path, sheet_name="ASIGNACION", header=None)
                    except Exception:
                        print(f"Pestaña 'ASIGNACION' no encontrada en {archivo}. Usando la primera pestaña.")
                        df = pd.read_excel(archivo_path, sheet_name=0, header=None)

                    # Ajustar encabezado
                    for i in range(3):  # Intentar con las primeras tres filas para buscar encabezados
                        if not df.iloc[i].isnull().all():
                            df.columns = df.iloc[i]
                            df = df[i + 1:].reset_index(drop=True)
                            break

                    # Extraer columnas relevantes
                    df_filtrado = extraer_relevante(df, archivo)
                    datos_filtrados.append(df_filtrado)
                    print(f"Archivo procesado: {archivo}")
                except Exception as e:
                    print(f"No se pudo procesar el archivo {archivo}: {e}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    # Consolidar todos los datos filtrados en un único DataFrame
    if datos_filtrados:
        df_consolidado = pd.concat(datos_filtrados, ignore_index=True)
        
        # Guardar el DataFrame consolidado en un archivo Excel
        df_consolidado.to_excel(output_file, index=False)
        print(f"Consolidación y filtrado completados. Archivo guardado en: {output_file}")
    else:
        print("No se encontraron datos relevantes para consolidar.")

# Ejecutar la función
consolidar_archivos_filtrados(input_folder, output_file)
