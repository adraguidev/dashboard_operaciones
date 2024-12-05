from src.utils.mongo_uploader import MongoUploader
from config.settings import MODULES, MODULE_FOLDERS
import pandas as pd
import os
from datetime import datetime

def migrate_data():
    """Migra datos históricos de Excel a MongoDB."""
    try:
        uploader = MongoUploader()
        
        # Migrar cada módulo excepto SPE
        for module, folder in MODULE_FOLDERS.items():
            if module != 'SPE':
                print(f"\nProcesando módulo: {module}")
                file_path = os.path.join(folder, f"Consolidado_{module}_CRUZADO.xlsx")
                
                if os.path.exists(file_path):
                    collection_name = f"consolidado_{module.lower()}"
                    metadata = {
                        'fecha_actualizacion': datetime.now(),
                        'fuente': file_path,
                        'version': '1.0'
                    }
                    uploader.upload_file(file_path, collection_name, metadata)
                else:
                    print(f"Archivo no encontrado: {file_path}")
        
        print("\n✅ Migración completada")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {str(e)}")

if __name__ == "__main__":
    migrate_data()