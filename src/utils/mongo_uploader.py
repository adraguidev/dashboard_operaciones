import pandas as pd
from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo.operations import InsertOne
import time

class MongoUploader:
    def __init__(self, mongo_uri=None):
        # Cargar variables de entorno
        load_dotenv()
        
        if mongo_uri is None:
            # Construir URI desde variables de entorno
            base_uri = os.getenv('MONGODB_URI')
            password = os.getenv('MONGODB_PASSWORD')
            if not base_uri or not password:
                raise ValueError("Variables de entorno MONGODB_URI y MONGODB_PASSWORD no configuradas")
            
            # Reemplazar placeholder con contraseña real
            mongo_uri = base_uri.replace('<db_password>', password)
        
        # Configurar timeouts más largos y reintentos
        self.client = MongoClient(
            mongo_uri,
            connectTimeoutMS=30000,
            socketTimeoutMS=None,  # Sin límite de tiempo para operaciones
            serverSelectionTimeoutMS=30000,
            retryWrites=True,
            retryReads=True,
            maxPoolSize=None,  # Sin límite en el pool de conexiones
            waitQueueTimeoutMS=30000
        )
        self.db = self.client['migraciones_db']
        
        # Verificar conexión
        try:
            self.client.admin.command('ping')
            print("✅ Conexión exitosa a MongoDB")
        except Exception as e:
            print(f"❌ Error de conexión a MongoDB: {str(e)}")
            raise

    def clean_data_for_mongo(self, df):
        """
        Limpia y prepara los datos para MongoDB.
        Todas las fechas se convierten al formato dd/mm/yyyy.
        """
        # Crear una copia para no modificar el original
        df = df.copy()
        
        # Lista de formatos de fecha conocidos
        date_formats = [
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y/%m/%d',
            '%d/%m/%Y %H:%M:%S',
            '%Y-%m-%d %H:%M:%S'
        ]
        
        # Convertir todas las columnas de fecha
        for column in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[column]):
                # Para columnas ya en formato datetime
                df[column] = df[column].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else None
                )
            elif isinstance(df[column].dtype, pd.StringDtype) or df[column].dtype == object:
                # Para columnas que podrían contener fechas como strings
                if df[column].notna().any():
                    # Intentar cada formato conocido
                    for date_format in date_formats:
                        try:
                            temp_dates = pd.to_datetime(
                                df[column], 
                                format=date_format, 
                                errors='coerce',
                                dayfirst=True  # Asegurar que el día va primero
                            )
                            if not temp_dates.isna().all():  # Si algunas conversiones fueron exitosas
                                df[column] = temp_dates.apply(
                                    lambda x: x.strftime('%d/%m/%Y') if pd.notnull(x) else None
                                )
                                break
                        except:
                            continue

        # Convertir NaN/NaT a None (null en MongoDB)
        df = df.replace({np.nan: None, pd.NaT: None})
        
        return df

    def upload_file(self, file_path, collection_name):
        """
        Sube un archivo Excel a MongoDB de manera optimizada.
        """
        max_retries = 3
        retry_delay = 5  # segundos
        
        for attempt in range(max_retries):
            try:
                print(f"\nProcesando {os.path.basename(file_path)}...")
                
                # Leer el archivo Excel
                df = pd.read_excel(file_path)
                total_records = len(df)
                print(f"Registros totales a procesar: {total_records}")

                # Reducir el tamaño del lote para archivos grandes
                batch_size = min(2000, max(100, total_records // 100))
                print(f"Tamaño de lote ajustado: {batch_size}")

                # Limpiar y preparar datos para MongoDB
                df = self.clean_data_for_mongo(df)

                # Metadata común
                metadata = {
                    'fecha_actualizacion': datetime.now(),
                    'archivo_origen': os.path.basename(file_path),
                    'total_registros': total_records
                }

                # 1. Preparar colecciones
                collection = self.db[collection_name]
                historical_collection = self.db[f"{collection_name}_historical"]
                
                # 2. Procesar en lotes para optimizar memoria
                bulk_ops_main = []
                historical_records = []
                
                for i in range(0, total_records, batch_size):
                    try:
                        # Obtener slice del DataFrame
                        batch_df = df.iloc[i:i + batch_size]
                        batch_records = batch_df.to_dict('records')
                        
                        # Preparar operaciones en bulk
                        bulk_ops_main.extend([
                            InsertOne(record) for record in batch_records
                        ])
                        
                        # Preparar registro histórico
                        historical_batch = {
                            'metadata': {
                                **metadata,
                                'batch_number': (i // batch_size) + 1,
                                'registros_en_lote': len(batch_records),
                                'rango_registros': f"{i + 1}-{min(i + batch_size, total_records)}"
                            },
                            'data': batch_records
                        }
                        historical_records.append(historical_batch)
                        
                        # Mostrar progreso
                        print(f"Procesados: {min(i + batch_size, total_records)}/{total_records} registros")
                        
                        # Subir lotes intermedios si son muchos registros
                        if len(bulk_ops_main) >= 10000:
                            print("Subiendo lote intermedio...")
                            collection.bulk_write(bulk_ops_main, ordered=False)
                            bulk_ops_main = []
                    
                    except Exception as batch_error:
                        print(f"Error en lote {i//batch_size + 1}: {str(batch_error)}")
                        continue

                # 3. Ejecutar operaciones finales en bulk
                print("\nActualizando colección principal...")
                collection.delete_many({})  # Limpiar colección actual
                if bulk_ops_main:
                    collection.bulk_write(bulk_ops_main, ordered=False)
                
                print("\nGuardando histórico...")
                if historical_records:
                    # Subir histórico en lotes más pequeños
                    for i in range(0, len(historical_records), 10):
                        historical_batch = historical_records[i:i + 10]
                        historical_collection.insert_many(historical_batch, ordered=False)
                        print(f"Histórico: {min(i + 10, len(historical_records))}/{len(historical_records)} lotes")

                print(f"✅ Datos actualizados en {collection_name}")
                print(f"✅ Histórico guardado en {collection_name}_historical")
                return  # Éxito, salir del bucle de reintentos
                
            except Exception as e:
                print(f"❌ Intento {attempt + 1}/{max_retries} falló: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Incrementar el tiempo de espera exponencialmente
                else:
                    print(f"❌ Error al subir {file_path} después de {max_retries} intentos")
                    raise

    def upload_all_consolidated_files(self):
        """
        Sube todos los archivos consolidados y cruzados a MongoDB.
        """
        carpeta_descargas = "C:/report_download/descargas/"
        archivos_a_subir = {
            'consolidado_ccm': f"{carpeta_descargas}/CCM/Consolidado_CCM_CRUZADO.xlsx",
            'consolidado_prr': f"{carpeta_descargas}/PRR/Consolidado_PRR_CRUZADO.xlsx",
            'consolidado_ccm_esp': f"{carpeta_descargas}/CCM-ESP/Consolidado_CCM-ESP_CRUZADO.xlsx",
            'consolidado_sol': f"{carpeta_descargas}/SOL/Consolidado_SOL_CRUZADO.xlsx"
        }
        
        # Procesar archivos en paralelo
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.upload_file, file_path, collection_name): collection_name
                for collection_name, file_path in archivos_a_subir.items()
                if os.path.exists(file_path)
            }
            
            for future in as_completed(futures):
                collection_name = futures[future]
                try:
                    future.result()
                except Exception as e:
                    print(f"❌ Error procesando {collection_name}: {str(e)}")

    def get_latest_update(self, collection_name):
        """
        Obtiene la fecha de la última actualización de una colección.
        """
        historical_collection = self.db[f"{collection_name}_historical"]
        latest = historical_collection.find_one(
            {},
            sort=[('metadata.fecha_actualizacion', -1)],
            projection={'metadata.fecha_actualizacion': 1}
        )
        return latest['metadata']['fecha_actualizacion'] if latest else None

    def get_historical_data(self, collection_name, fecha_actualizacion):
        """
        Recupera datos históricos completos para una fecha específica.
        """
        historical_collection = self.db[f"{collection_name}_historical"]
        
        # Encontrar todos los lotes para la fecha dada
        batches = historical_collection.find({
            'metadata.fecha_actualizacion': fecha_actualizacion
        }).sort('metadata.batch_number', 1)
        
        # Combinar todos los registros de los lotes
        all_records = []
        for batch in batches:
            all_records.extend(batch['data'])
        
        return all_records 