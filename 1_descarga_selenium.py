import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time
import os
import glob

# Configuración del WebDriver
webdriver_path = "C:/chromedriver-win64/chromedriver.exe"
download_dir = os.path.abspath("./descargas_temporales/")
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_experimental_option("prefs", {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})
service = Service(webdriver_path)

driver = webdriver.Chrome(service=service, options=chrome_options)
driver.set_page_load_timeout(600)  # Timeout de carga de página (en segundos)
driver.implicitly_wait(10)        # Espera implícita para encontrar elementos (en segundos)

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
output_folders = {}
for tipo, nombre in tipos_tramite.items():
    folder_name = f"./descargas/{nombre}/"
    output_folders[tipo] = os.path.abspath(folder_name)
    os.makedirs(output_folders[tipo], exist_ok=True)

# Generar URLs por partes
def generar_urls_por_partes():
    urls_por_partes = {}
    for tipo in tipos_tramite.keys():
        urls_por_partes[tipo] = []
        for anio in anios:
            for estado in estados_tramite:
                url = f"http://Yacosta:Yoky2024.4@172.27.230.27/ReportServer?" \
                      f"%2FAGV_PTP%2FRPT_INMIGRA_PTP_REGUL_CCM&nidtipoTramite={tipo}&anio={anio}&EstadoTramite={estado}" \
                      f"&rs:ParameterLanguage=&rs:Command=Render&rs:Format=CSV&rc:ItemPath=Tablix1"
                urls_por_partes[tipo].append((url, anio, estado))
    return urls_por_partes

urls_por_partes = generar_urls_por_partes()

# Descargar con reintentos
def descargar_con_reintentos(driver, url, max_reintentos=3):
    for intento in range(max_reintentos):
        try:
            print(f"Intento {intento + 1} de {max_reintentos} para: {url}")
            driver.get(url)
            time.sleep(10)
            return
        except Exception as e:
            print(f"Error en intento {intento + 1}: {e}")
            time.sleep(30)
    print(f"Falló la descarga tras {max_reintentos} intentos: {url}")

# Descargar archivos
def descargar_por_partes(tipo, urls, output_folder):
    for url, anio, estado in urls:
        new_filename = f"{anio}_{estado}.csv"
        new_filepath = os.path.join(output_folder, new_filename)
        
        if os.path.exists(new_filepath):
            print(f"[{tipos_tramite[tipo]}] Archivo ya existe: {new_filename}. Saltando...")
            continue

        try:
            print(f"[{tipos_tramite[tipo]}] Descargando: Año {anio}, Estado {estado}")
            descargar_con_reintentos(driver, url)

            downloaded_files = glob.glob(f"{download_dir}/*")
            if not downloaded_files:
                print("No se encontraron archivos descargados.")
                continue

            downloaded_file = max(downloaded_files, key=os.path.getctime)
            os.rename(downloaded_file, new_filepath)
            print(f"Archivo guardado en: {new_filepath}")
        except Exception as e:
            print(f"Error al procesar Año {anio}, Estado {estado}: {e}")

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

# Descargar y consolidar por cada tipo
for tipo, urls in urls_por_partes.items():
    descargar_por_partes(tipo, urls, output_folders[tipo])
    consolidate_csv(output_folders[tipo], f"Consolidado_{tipos_tramite[tipo]}.xlsx")

driver.quit()

