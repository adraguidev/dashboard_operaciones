import pandas as pd
import os

base_folder = 'descargas'
module_folders = {
    'CCM': os.path.join(base_folder, 'CCM'),
    'PRR': os.path.join(base_folder, 'PRR'),
    'CCM-ESP': os.path.join(base_folder, 'CCM-ESP'),
    'CCM-LEY': os.path.join(base_folder, 'CCM-LEY'),  # Añadido CCM-LEY
    'SOL': os.path.join(base_folder, 'SOL'),
}

def load_consolidated(module_name):
    folder = module_folders[module_name]
    for file in os.listdir(folder):
        if file.startswith(f"Consolidado_{module_name}_CRUZADO") and file.endswith(".xlsx"):
            file_path = os.path.join(folder, file)
            return pd.read_excel(file_path)
    return None
