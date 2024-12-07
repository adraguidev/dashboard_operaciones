from descarga import descargar_y_consolidar
from manejo_reportes import manejar_reportes
from gestionar_consolidados import procesar_consolidados
from cruces import procesar_cruces_combinados
from consolidador import ejecutar_consolidacion
from src.utils.mongo_uploader import MongoUploader
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Simplificar la verificación de directorios
descargas_dir = "descargas"  # Ruta relativa

print(f"Verificando directorio de descargas: {descargas_dir}")

# Verificar que existan las carpetas necesarias
for carpeta in ['CCM', 'PRR', 'CCM-ESP', 'SOL']:
    ruta = os.path.join(descargas_dir, carpeta)
    if not os.path.exists(ruta):
        print(f"Creando directorio: {ruta}")
        os.makedirs(ruta, exist_ok=True)

def mostrar_menu():
    print("\n=== MENÚ DE OPCIONES ===")
    print("1. Descargar y consolidar datos")
    print("2. Consolidar archivos CCM y PRR")
    print("3. Manejo de reportes evaluados")
    print("4. Procesar consolidados iniciales")
    print("5. Realizar cruces combinados")
    print("6. Ejecutar todos los pasos")
    print("7. Subir datos a MongoDB")
    print("8. Verificar rutas de archivos")
    print("0. Salir")
    print("Nota: Puedes seleccionar múltiples opciones separadas por comas (ej: 1,3,5)")

def subir_a_mongodb():
    try:
        print(f"\nVerificando archivos en: {descargas_dir}")
        
        # Verificar que exista el directorio de descargas
        if not os.path.exists(descargas_dir):
            print(f"❌ Error: No se encuentra el directorio de descargas en: {descargas_dir}")
            return
            
        # Las variables de entorno ya estarán disponibles automáticamente
        uploader = MongoUploader()
        
        # Mostrar últimas actualizaciones
        colecciones = ['consolidado_ccm', 'consolidado_prr', 'consolidado_ccm_esp', 'consolidado_sol']
        print("\nÚltimas actualizaciones:")
        for col in colecciones:
            ultima_fecha = uploader.get_latest_update(col)
            if ultima_fecha:
                print(f"- {col}: {ultima_fecha.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"- {col}: Sin actualizaciones previas")
        
        # Confirmar subida
        respuesta = input("\n¿Desea proceder con la actualización? (s/n): ").lower().strip()
        if respuesta != 's':
            print("Operación cancelada.")
            return
        
        # Subir archivos
        uploader.upload_all_consolidated_files()
        
    except Exception as e:
        print(f"❌ Error al subir datos a MongoDB: {str(e)}")

def ejecutar_paso(opcion):
    if opcion == 1:
        print("\n>>> Ejecutando: Descargar y consolidar datos")
        descargar_y_consolidar()
    elif opcion == 2:
        print("\n>>> Ejecutando: Consolidar archivos CCM y PRR")
        ejecutar_consolidacion()
    elif opcion == 3:
        print("\n>>> Ejecutando: Manejo de reportes evaluados")
        manejar_reportes()
    elif opcion == 4:
        print("\n>>> Ejecutando: Procesar consolidados iniciales")
        procesar_consolidados()
    elif opcion == 5:
        print("\n>>> Ejecutando: Realizar cruces combinados")
        procesar_cruces_combinados()
    elif opcion == 6:
        print("\n>>> Ejecutando: Ejecutar todos los pasos")
        ejecutar_todos_pasos()
    elif opcion == 7:
        print("\n>>> Ejecutando: Subir datos a MongoDB")
        subir_a_mongodb()
    elif opcion == 8:
        print("\n>>> Ejecutando: Verificar rutas de archivos")
        verificar_rutas()

def ejecutar_todos_pasos():
    print("\n=== Ejecutando todos los pasos ===")
    for paso in range(1, 6):
        ejecutar_paso(paso)

def verificar_rutas():
    print(f"Directorio base: {descargas_dir}")
    print("\nVerificando archivos:")
    for carpeta in ['CCM', 'PRR', 'CCM-ESP', 'SOL']:
        ruta = os.path.join(descargas_dir, carpeta)
        archivo = os.path.join(ruta, f"Consolidado_{carpeta}_CRUZADO.xlsx")
        print(f"- {archivo}: {'✅ Existe' if os.path.exists(archivo) else '❌ No existe'}")

def main():
    while True:
        mostrar_menu()
        seleccion = input("\nSelecciona las opciones deseadas: ")
        
        if seleccion.strip() == "0":
            print("\nSaliendo del programa...")
            break
        
        if seleccion.strip() == "6":
            ejecutar_todos_pasos()
            continue
        
        try:
            # Convertir la entrada en una lista de números
            opciones = [int(opt.strip()) for opt in seleccion.split(",")]
            
            # Validar que las opciones sean válidas
            if any(opt < 0 or opt > 8 for opt in opciones):
                print("\n❌ Error: Algunas opciones no son válidas. Por favor intenta nuevamente.")
                continue
                
            # Ejecutar cada paso seleccionado
            for opcion in opciones:
                ejecutar_paso(opcion)
                
            print("\n✅ Proceso(s) completado(s)")
            
        except ValueError:
            print("\n❌ Error: Por favor ingresa números válidos separados por comas.")
            continue

if __name__ == "__main__":
    print("=== Sistema de Procesamiento de Datos ===")
    main()
