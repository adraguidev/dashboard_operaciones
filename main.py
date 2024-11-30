from descarga import descargar_y_consolidar
from manejo_reportes import manejar_reportes
from gestionar_consolidados import procesar_consolidados
from cruces import procesar_cruces_combinados

def main():
    print("=== Inicio del proceso ===")

    # Paso 1: Descargar y consolidar archivos CSV
    print("\nPaso 1: Descargar y consolidar datos")
    descargar_y_consolidar()

    # Paso 2: Manejo de reportes evaluados
    print("\nPaso 2: Manejo de reportes evaluados")
    manejar_reportes()

    # Paso 3: Procesar consolidados iniciales
    print("\nPaso 3: Procesar consolidados iniciales")
    procesar_consolidados()

    # Paso 4: Realizar cruces combinados
    print("\nPaso 4: Realizar cruces combinados")
    procesar_cruces_combinados()

    print("\n=== Proceso completado ===")

if __name__ == "__main__":
    main()
