import pandas as pd
import os
import shutil
from file_utils import confirmar_sobrescritura

# Configuración de carpetas y archivos
current_dir = os.path.dirname(os.path.abspath(__file__))
descargas_dir = os.path.join(current_dir, "descargas")

input_folders = {
    "CCM": r"\\172.27.230.89\produccion_evaluadores_sgin\ASIGNACIONES\ASIGNACION CAMPAÑA",
    "PRR": r"\\172.27.230.55\analistas sgin\ASIGNACIONES - PRR"
}
output_files = {
    "CCM": os.path.join(descargas_dir, "CCM", "consolidado_filtrado_ccm.xlsx"),
    "PRR": os.path.join(descargas_dir, "PRR", "consolidado_filtrado_prr.xlsx")
}
output_paths = {
    "CCM": [os.path.join(descargas_dir, "CCM"), os.path.join(descargas_dir, "CCM-ESP")],
    "PRR": [os.path.join(descargas_dir, "PRR")]
}

# Crear carpetas si no existen
os.makedirs(descargas_dir, exist_ok=True)
for paths in output_paths.values():
    for path in paths:
        os.makedirs(path, exist_ok=True)

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
    return estado.strip().upper() if isinstance(estado, str) else estado

def extraer_relevante(df, archivo_origen):
    """Extrae las columnas EXPEDIENTE, ESTADO, DESCRIPCION y FECHA DE TRABAJO si existen."""
    df.columns = [col.strip().upper() if isinstance(col, str) else str(col).strip() for col in df.columns]
    columnas_necesarias = ["EXPEDIENTE", "ESTADO", "DESCRIPCION (OPCIONAL)", "DESCRIPCION", "FECHA DE TRABAJO"]
    columnas_presentes = [col for col in columnas_necesarias if col in df.columns]
    df_filtrado = df[columnas_presentes].copy()

    if "DESCRIPCION (OPCIONAL)" in df_filtrado:
        df_filtrado.rename(columns={"DESCRIPCION (OPCIONAL)": "DESCRIPCION"}, inplace=True)

    if "EXPEDIENTE" in df_filtrado:
        df_filtrado = df_filtrado[df_filtrado["EXPEDIENTE"].apply(lambda x: isinstance(x, str) and x.startswith("LM"))]

    if "ESTADO" in df_filtrado:
        df_filtrado["ESTADO"] = df_filtrado["ESTADO"].apply(normalizar_estado)
        df_filtrado = df_filtrado[df_filtrado["ESTADO"].isin([estado.upper() for estado in estados_validos])]

    df_filtrado["ARCHIVO_ORIGEN"] = archivo_origen
    return df_filtrado

def consolidar_archivos_filtrados(input_folder, output_file):
    datos_filtrados = []
    archivos = [archivo for archivo in os.listdir(input_folder) if os.path.isfile(os.path.join(input_folder, archivo))]
    total_archivos = len(archivos)

    for idx, archivo in enumerate(archivos, start=1):
        archivo_path = os.path.join(input_folder, archivo)
        if archivo.endswith((".xlsx", ".xlsm")) and not archivo.startswith("~$"):
            print(f"Procesando archivo {idx}/{total_archivos}: {archivo}")
            try:
                try:
                    df = pd.read_excel(archivo_path, sheet_name="ASIGNACION", header=None)
                except Exception:
                    print(f"Pestaña 'ASIGNACION' no encontrada en {archivo}. Usando la primera pestaña.")
                    df = pd.read_excel(archivo_path, sheet_name=0, header=None)

                for i in range(3):
                    if not df.iloc[i].isnull().all():
                        df.columns = df.iloc[i]
                        df = df[i + 1:].reset_index(drop=True)
                        break

                df_filtrado = extraer_relevante(df, archivo)
                datos_filtrados.append(df_filtrado)
            except Exception as e:
                print(f"No se pudo procesar el archivo {archivo}: {e}")

    if datos_filtrados:
        df_consolidado = pd.concat(datos_filtrados, ignore_index=True)
        df_consolidado.to_excel(output_file, index=False)
        print(f"Archivo consolidado guardado en: {output_file}")
        return output_file
    else:
        print("No se encontraron datos relevantes.")
        return None

def mover_archivo(output_file, destinos):
    for destino in destinos:
        # Verificar que el archivo de destino no sea el mismo que el archivo de origen
        destino_archivo = os.path.join(destino, os.path.basename(output_file))
        if os.path.abspath(output_file) != os.path.abspath(destino_archivo):
            shutil.copy(output_file, destino)
            print(f"Archivo copiado a: {destino}")
        else:
            print(f"El archivo ya se encuentra en {destino}, no se realizó la copia.")

# Renombrar la ejecución directa a una función principal
def ejecutar_consolidacion():
    # Verificar archivos que se crearán
    if not confirmar_sobrescritura(output_files):
        print("Proceso de consolidación omitido.")
        return
        
    for key in input_folders:
        print(f"\nIniciando procesamiento para {key}...")
        output_file = output_files[key]
        destinos = output_paths[key]
        archivo_generado = consolidar_archivos_filtrados(input_folders[key], output_file)
        if archivo_generado:
            mover_archivo(archivo_generado, destinos)
        print(f"Procesamiento para {key} completado.")

# El resto del código permanece igual...
