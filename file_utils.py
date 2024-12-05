import os

def confirmar_sobrescritura(archivos):
    """
    Verifica si los archivos existen y pide confirmación para sobrescribir.
    
    Args:
        archivos: Lista de rutas de archivos o diccionario con rutas de archivos
        
    Returns:
        bool: True si se debe proceder, False si se debe omitir
    """
    archivos_list = archivos if isinstance(archivos, list) else list(archivos.values())
    archivos_existentes = [arch for arch in archivos_list if os.path.exists(arch)]
    
    if archivos_existentes:
        print("\nSe encontraron los siguientes archivos existentes:")
        for archivo in archivos_existentes:
            print(f"- {archivo}")
        
        while True:
            respuesta = input("\n¿Desea sobrescribir estos archivos? (s/n): ").lower().strip()
            if respuesta in ['s', 'n']:
                return respuesta == 's'
            print("Por favor, responde 's' para sí o 'n' para no.")
    
    return True 