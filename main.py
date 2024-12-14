from descarga import descargar_y_consolidar
from manejo_reportes import manejar_reportes
from gestionar_consolidados import procesar_consolidados
from cruces import procesar_cruces_combinados
from consolidador import ejecutar_consolidacion
from src.utils.mongo_uploader import MongoUploader
import os
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.theme import Theme
from rich.prompt import Prompt

# Configurar tema personalizado
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
})

console = Console(theme=custom_theme)

# Función para imprimir con estilo consistente
def print_styled(text, style=""):
    console.print(text, style=style)

# Cargar variables de entorno
load_dotenv()

# Simplificar la verificación de directorios
descargas_dir = "descargas"  # Ruta relativa

print_styled(f"Verificando directorio de descargas: {descargas_dir}", style="info")

# Verificar que existan las carpetas necesarias
for carpeta in ['CCM', 'PRR', 'CCM-ESP', 'SOL']:
    ruta = os.path.join(descargas_dir, carpeta)
    if not os.path.exists(ruta):
        print_styled(f"Creando directorio: {ruta}", style="info")
        os.makedirs(ruta, exist_ok=True)

def mostrar_menu():
    print_styled("\n=== MENÚ DE OPCIONES ===", style="bold cyan")
    print_styled("1. Descargar y consolidar datos")
    print_styled("2. Consolidar archivos CCM y PRR")
    print_styled("3. Manejo de reportes evaluados")
    print_styled("4. Procesar consolidados iniciales")
    print_styled("5. Realizar cruces combinados")
    print_styled("6. Subir datos a MongoDB")
    print_styled("7. Ejecutar todos los pasos")
    print_styled("8. Verificar rutas de archivos")
    print_styled("0. Salir")
    print_styled("Nota: Puedes seleccionar múltiples opciones separadas por comas (ej: 1,3,5)", style="yellow")

def subir_a_mongodb():
    try:
        print_styled(f"\nVerificando archivos en: {descargas_dir}", style="info")
        
        if not os.path.exists(descargas_dir):
            print_styled(f"❌ Error: No se encuentra el directorio de descargas en: {descargas_dir}", style="error")
            return
            
        uploader = MongoUploader()
        
        colecciones = ['consolidado_ccm', 'consolidado_prr', 'consolidado_ccm_esp', 'consolidado_sol']
        print_styled("\nÚltimas actualizaciones:", style="info")
        for col in colecciones:
            ultima_fecha = uploader.get_latest_update(col)
            if ultima_fecha:
                print_styled(f"- {col}: {ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print_styled(f"- {col}: Sin actualizaciones previas", style="warning")
        
        respuesta = Prompt.ask("\n¿Desea proceder con la actualización?", choices=["s", "n"], default="n")
        if respuesta != 's':
            print_styled("Operación cancelada.", style="warning")
            return
        
        uploader.upload_all_consolidated_files()
        
    except Exception as e:
        print_styled(f"❌ Error al subir datos a MongoDB: {str(e)}", style="error")

def ejecutar_paso(opcion):
    if opcion == 1:
        print_styled("\n>>> Ejecutando: Descargar y consolidar datos")
        descargar_y_consolidar()
    elif opcion == 2:
        print_styled("\n>>> Ejecutando: Consolidar archivos CCM y PRR")
        ejecutar_consolidacion()
    elif opcion == 3:
        print_styled("\n>>> Ejecutando: Manejo de reportes evaluados")
        manejar_reportes()
    elif opcion == 4:
        print_styled("\n>>> Ejecutando: Procesar consolidados iniciales")
        procesar_consolidados()
    elif opcion == 5:
        print_styled("\n>>> Ejecutando: Realizar cruces combinados")
        procesar_cruces_combinados()
    elif opcion == 6:
        print_styled("\n>>> Ejecutando: Subir datos a MongoDB")
        subir_a_mongodb()
    elif opcion == 7:
        print_styled("\n>>> Ejecutando: Todos los pasos en secuencia")
        ejecutar_todos_pasos()
    elif opcion == 8:
        print_styled("\n>>> Ejecutando: Verificar rutas de archivos")
        verificar_rutas()

def ejecutar_todos_pasos():
    print_styled("\n=== Ejecutando todos los pasos ===", style="bold cyan")
    # Ejecutar solo los pasos del 1 al 5, y luego MongoDB (6)
    for paso in range(1, 6):
        print_styled(f"\n>> Paso {paso} de 6", style="info")
        if paso == 1:
            descargar_y_consolidar()
        elif paso == 2:
            ejecutar_consolidacion()
        elif paso == 3:
            manejar_reportes()
        elif paso == 4:
            procesar_consolidados()
        elif paso == 5:
            procesar_cruces_combinados()
    
    # Ejecutar la subida a MongoDB como último paso
    print_styled("\n>> Paso 6 de 6", style="info")
    subir_a_mongodb()

def verificar_rutas():
    print_styled(f"Directorio base: {descargas_dir}", style="info")
    print_styled("\nVerificando archivos:", style="info")
    for carpeta in ['CCM', 'PRR', 'CCM-ESP', 'SOL']:
        ruta = os.path.join(descargas_dir, carpeta)
        archivo = os.path.join(ruta, f"Consolidado_{carpeta}_CRUZADO.xlsx")
        print_styled(f"- {archivo}: {'✅ Existe' if os.path.exists(archivo) else '❌ No existe'}", style="info")

def main():
    while True:
        mostrar_menu()
        seleccion = input("\nSelecciona las opciones deseadas: ")
        
        if seleccion.strip() == "0":
            print_styled("\nSaliendo del programa...", style="info")
            break
        
        if seleccion.strip() == "7":
            ejecutar_todos_pasos()
            continue
        
        try:
            opciones = [int(opt.strip()) for opt in seleccion.split(",")]
            
            if any(opt < 0 or opt > 8 for opt in opciones):
                print_styled("\n❌ Error: Algunas opciones no son válidas. Por favor intenta nuevamente.", style="error")
                continue
                
            for opcion in opciones:
                ejecutar_paso(opcion)
                
            print_styled("\n✅ Proceso(s) completado(s)", style="success")
            
        except ValueError:
            print_styled("\n❌ Error: Por favor ingresa números válidos separados por comas.", style="error")
            continue

if __name__ == "__main__":
    print_styled("=== Sistema de Procesamiento de Datos ===", style="bold cyan")
    main()
