import pandas as pd
import requests
import os
import glob
import time
from concurrent.futures import ThreadPoolExecutor
from requests_ntlm import HttpNtlmAuth
from file_utils import confirmar_sobrescritura

# Configuración de parámetros
tipos_tramite = {
    58: "CCM",
    57: "PRR",
    317: "CCM-ESP",
    55: "SOL"
}
anios = [2024, 2023, 2022, 2021, 2020, 2019, 2018]
estados_tramite = ["A", "P", "B", "R", "D", "E", "N"]

# Crear carpetas dinámicas para guardar archivos
def crear_carpetas():
    output_folders = {}
    for tipo, nombre in tipos_tramite.items():
        folder_name = f"./descargas/{nombre}/"
        output_folders[tipo] = os.path.abspath(folder_name)
        os.makedirs(output_folders[tipo], exist_ok=True)
    return output_folders

# Generar URLs por partes
def generar_urls_por_partes():
    urls_por_partes = {}
    for tipo in tipos_tramite.keys():
        urls_por_partes[tipo] = []
        for anio in anios:
            for estado in estados_tramite:
                url = f"http://172.27.230.27/ReportServer?" \
                      f"%2FAGV_PTP%2FRPT_INMIGRA_PTP_REGUL_CCM&nidtipoTramite={tipo}&anio={anio}&EstadoTramite={estado}" \
                      f"&rs:ParameterLanguage=&rs:Command=Render&rs:Format=CSV&rc:ItemPath=Tablix1"
                urls_por_partes[tipo].append((url, anio, estado))
    return urls_por_partes

# Descargar con requests y reintentos
def descargar_con_reintentos(url, output_path, max_reintentos=3, timeout=600):
    delay = 5  # Espera inicial de 5 segundos
    for intento in range(max_reintentos):
        try:
            print(f"Intento {intento + 1} de {max_reintentos} para: {url}")
            response = requests.get(
                url,
                timeout=timeout,
                auth=HttpNtlmAuth('Yacosta', 'Yoky2024.4')  # Credenciales NTLM
            )
            response.raise_for_status()  # Verifica si hubo errores en la solicitud
            with open(output_path, 'wb') as file:
                file.write(response.content)
            print(f"Archivo descargado correctamente: {output_path}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error en intento {intento + 1}: {e}")
            time.sleep(delay)
            delay *= 2  # Incrementa exponencialmente el tiempo de espera
    print(f"Falló la descarga tras {max_reintentos} intentos: {url}")
    return False

# Descargar en paralelo
def descargar_en_paralelo(tipo, urls, output_folder, max_workers=7):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for url, anio, estado in urls:
            output_path = os.path.join(output_folder, f"{anio}_{estado}.csv")
            if os.path.exists(output_path):
                print(f"[{tipos_tramite[tipo]}] Archivo ya existe: {output_path}. Saltando...")
                continue
            futures.append(executor.submit(descargar_con_reintentos, url, output_path))
        for future in futures:
            future.result()  # Espera a que todas las descargas terminen

# Consolidar archivos en Excel
def consolidate_csv(folder_path, output_filename):
    try:
        csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
        if not csv_files:
            print(f"No se encontraron archivos CSV en {folder_path}.")
            return

        consolidated_data = []
        for file in csv_files:
            try:
                print(f"Procesando: {file}")
                df = pd.read_csv(file, skiprows=3, sep=",", low_memory=False)
                if 'Dependencia' in df.columns:
                    df = df[df['Dependencia'].isin(['LIMA', 'MIRAFLORES', 'LIMA SUR', 'LIMA NORTE'])]
                consolidated_data.append(df)
            except Exception as e:
                print(f"Error al procesar {file}: {e}")

        if consolidated_data:
            final_df = pd.concat(consolidated_data, ignore_index=True)
            output_file = os.path.join(folder_path, output_filename)
            final_df.to_excel(output_file, index=False)
            print(f"Consolidado guardado en: {output_file}")
        else:
            print(f"No se generó ningún consolidado para {folder_path}.")
    except Exception as e:
        print(f"Error al consolidar archivos: {e}")

# Descargar y consolidar archivos
def descargar_y_consolidar():
    output_folders = crear_carpetas()
    
    # Verificar archivos consolidados finales que se crearán
    archivos_consolidados = {
        tipo: os.path.join(folder, f"Consolidado_{tipos_tramite[tipo]}.xlsx")
        for tipo, folder in output_folders.items()
    }
    
    # Verificar archivos CSV existentes
    archivos_csv_existentes = {}
    for tipo, folder in output_folders.items():
        csv_files = glob.glob(os.path.join(folder, "*.csv"))
        if csv_files:
            archivos_csv_existentes[tipos_tramite[tipo]] = csv_files
    
    if archivos_csv_existentes:
        print("\nSe encontraron archivos CSV de descargas previas:")
        for tipo, archivos in archivos_csv_existentes.items():
            print(f"\n{tipo}:")
            for archivo in archivos:
                print(f"- {os.path.basename(archivo)}")
        
        while True:
            respuesta = input("\n¿Desea eliminar los archivos CSV existentes y descargar nuevamente? (s/n): ").lower().strip()
            if respuesta in ['s', 'n']:
                if respuesta == 's':
                    # Eliminar archivos CSV existentes
                    for archivos in archivos_csv_existentes.values():
                        for archivo in archivos:
                            try:
                                os.remove(archivo)
                                print(f"Eliminado: {os.path.basename(archivo)}")
                            except Exception as e:
                                print(f"Error al eliminar {archivo}: {e}")
                else:
                    print("Se conservarán los archivos CSV existentes.")
                break
            print("Por favor, responde 's' para sí o 'n' para no.")
    
    # Verificar si se desea sobrescribir los consolidados finales
    if not confirmar_sobrescritura(archivos_consolidados):
        print("Proceso de consolidación final omitido.")
        return
    
    urls_por_partes = generar_urls_por_partes()
    for tipo, urls in urls_por_partes.items():
        print(f"\nIniciando descargas en paralelo para {tipos_tramite[tipo]}...")
        
        # Verificar qué archivos CSV faltan
        folder = output_folders[tipo]
        archivos_existentes = {os.path.basename(f) for f in glob.glob(os.path.join(folder, "*.csv"))}
        
        # Filtrar URLs para descargar solo los archivos faltantes
        urls_faltantes = []
        for url, anio, estado in urls:
            nombre_archivo = f"{anio}_{estado}.csv"
            if nombre_archivo not in archivos_existentes:
                urls_faltantes.append((url, anio, estado))
        
        if not urls_faltantes:
            print(f"Todos los archivos CSV ya existen para {tipos_tramite[tipo]}.")
        else:
            print(f"Descargando {len(urls_faltantes)} archivos faltantes para {tipos_tramite[tipo]}...")
            descargar_en_paralelo(tipo, urls_faltantes, folder, max_workers=5)
        
        # Consolidar todos los CSV (tanto existentes como nuevos)
        consolidate_csv(folder, f"Consolidado_{tipos_tramite[tipo]}.xlsx")
