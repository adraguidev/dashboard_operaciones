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
            
            # Usar la URI directamente sin modificaciones
            mongo_uri = base_uri

        try:
            print("Intentando conexión a MongoDB...")
            print(f"URI de conexión: {mongo_uri.replace(password, '****')}")
            
            # Configuración corregida para cluster balanceado
            self.client = MongoClient(
                mongo_uri,
                connectTimeoutMS=30000,
                socketTimeoutMS=None,  # Sin límite de tiempo para operaciones
                serverSelectionTimeoutMS=30000,
                retryWrites=True,
                retryReads=True,
                maxPoolSize=None,  # Sin límite en el pool de conexiones
                waitQueueTimeoutMS=30000,
                appName='MigracionesApp',  # Identificador de la aplicación
                compressors=['zlib']  # Usar compresión
            )
            
            # Verificar conexión inmediatamente
            self.client.admin.command('ping')
            self.db = self.client['migraciones_db']
            print("✅ Conexión exitosa a MongoDB")
            
        except Exception as e:
            print(f"❌ Error de conexión a MongoDB: {str(e)}")
            print("\nVerificando posibles problemas:")
            print("1. ¿La URI de MongoDB es correcta?")
            print("2. ¿Tu IP está en la lista blanca de MongoDB Atlas?")
            print("3. ¿Tienes una conexión estable a internet?")
            print("4. ¿Las credenciales son correctas?")
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
        Sube un archivo Excel a MongoDB de manera optimizada para instancias serverless.
        """
        self.ensure_connection()
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"\nProcesando {os.path.basename(file_path)}...")
                
                # Leer el archivo Excel
                df = pd.read_excel(file_path)
                total_records = len(df)
                print(f"Registros totales a procesar: {total_records}")

                if df.empty:
                    raise ValueError(f"El archivo {file_path} está vacío")

                # Limpiar datos una sola vez
                df = self.clean_data_for_mongo(df)

                # Metadata común
                metadata = {
                    'fecha_actualizacion': datetime.now(),
                    'archivo_origen': os.path.basename(file_path),
                    'total_registros': total_records
                }

                # Preparar colecciones
                collection = self.db[collection_name]
                historical_collection = self.db[f"{collection_name}_historical"]

                # Optimizar tamaño de lote para serverless
                batch_size = 1000  # Tamaño más pequeño para evitar timeouts
                total_batches = (total_records + batch_size - 1) // batch_size

                print(f"\nProcesando {total_batches} lotes de {batch_size} registros cada uno")

                # Usar delete_many solo una vez al inicio
                print("\nLimpiando colección principal...")
                collection.delete_many({})

                # Insertar datos en lotes
                for i in range(0, total_records, batch_size):
                    end_idx = min(i + batch_size, total_records)
                    batch_df = df.iloc[i:end_idx]
                    batch_records = batch_df.to_dict('records')
                    
                    try:
                        # Insertar en colección principal
                        collection.insert_many(batch_records, ordered=False)
                        
                        # Guardar metadata sin los datos completos para ahorrar espacio
                        historical_metadata = {
                            'metadata': {
                                **metadata,
                                'batch_number': (i // batch_size) + 1,
                                'total_batches': total_batches,
                                'registros_en_lote': len(batch_records),
                                'rango_registros': f"{i + 1}-{end_idx}"
                            }
                        }
                        historical_collection.insert_one(historical_metadata)
                        
                        print(f"Progreso: {end_idx}/{total_records} registros procesados ({(end_idx/total_records*100):.1f}%)")
                        
                    except Exception as e:
                        print(f"Error en lote {i//batch_size + 1}: {str(e)}")
                        # Solo reconectar si es necesario
                        if "connection" in str(e).lower():
                            self.ensure_connection()
                        continue

                # Verificar integridad al final
                final_count = collection.count_documents({})
                if final_count != total_records:
                    print(f"⚠️ Advertencia: {final_count} registros en DB vs {total_records} en Excel")
                else:
                    print(f"\n✅ Datos actualizados en {collection_name}")
                    print(f"✅ Total registros: {final_count}")
                return

            except Exception as e:
                print(f"❌ Intento {attempt + 1}/{max_retries} falló: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    print(f"❌ Error al subir {file_path} después de {max_retries} intentos")
                    raise

    def upload_all_consolidated_files(self):
        """
        Sube todos los archivos consolidados y cruzados a MongoDB.
        """
        try:
            # Usar rutas relativas desde la carpeta del proyecto
            descargas_dir = "descargas"  # Carpeta relativa
            
            # Definir rutas relativas para cada archivo
            archivos_a_subir = {
                'consolidado_ccm': os.path.join(descargas_dir, "CCM", "Consolidado_CCM_CRUZADO.xlsx"),
                'consolidado_prr': os.path.join(descargas_dir, "PRR", "Consolidado_PRR_CRUZADO.xlsx"),
                'consolidado_ccm_esp': os.path.join(descargas_dir, "CCM-ESP", "Consolidado_CCM-ESP_CRUZADO.xlsx"),
                'consolidado_sol': os.path.join(descargas_dir, "SOL", "Consolidado_SOL_CRUZADO.xlsx")
            }
            
            # Mostrar estado actual y permitir selección
            print("\nEstado actual de las colecciones:")
            colecciones_disponibles = []
            for collection_name, file_path in archivos_a_subir.items():
                ultima_fecha = self.get_latest_update(collection_name)
                estado = "✅" if ultima_fecha else "❌"
                fecha_str = ultima_fecha.strftime('%Y-%m-%d %H:%M:%S') if ultima_fecha else "Sin actualizaciones"
                
                if os.path.exists(file_path):
                    colecciones_disponibles.append(collection_name)
                    print(f"{len(colecciones_disponibles)}. {collection_name}: {estado} Última actualización: {fecha_str}")
                else:
                    print(f"X. {collection_name}: Archivo no encontrado")
            
            # Solicitar selección al usuario
            print("\nSelecciona las colecciones a subir (separadas por comas) o 'todo' para subir todas:")
            seleccion = input("Ejemplo: 1,3 o 'todo': ").strip().lower()
            
            if not seleccion:
                print("Operación cancelada.")
                return
            
            colecciones_seleccionadas = []
            if seleccion == 'todo':
                colecciones_seleccionadas = colecciones_disponibles
            else:
                try:
                    indices = [int(i.strip()) - 1 for i in seleccion.split(',')]
                    colecciones_seleccionadas = [colecciones_disponibles[i] for i in indices if 0 <= i < len(colecciones_disponibles)]
                except (ValueError, IndexError):
                    print("❌ Selección inválida")
                    return
            
            # Confirmar selección
            print("\nSe subirán las siguientes colecciones:")
            for col in colecciones_seleccionadas:
                print(f"- {col}")
            
            confirmacion = input("\n¿Confirmar subida? (s/n): ").lower().strip()
            if confirmacion != 's':
                print("Operación cancelada.")
                return
            
            # Procesar archivos seleccionados
            for collection_name in colecciones_seleccionadas:
                file_path = archivos_a_subir[collection_name]
                try:
                    print(f"\nProcesando {collection_name}...")
                    self.upload_file(file_path, collection_name)
                except Exception as e:
                    print(f"❌ Error procesando {collection_name}: {str(e)}")
                    continue
                
        except Exception as e:
            print(f"❌ Error general al subir archivos: {str(e)}")

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

    def ensure_connection(self):
        """Asegura que la conexión esté activa, reconectando si es necesario"""
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                self.client.admin.command('ping')
                return True
            except Exception as e:
                print(f"Intento de reconexión {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    # Intentar recrear la conexión
                    self.__init__()
                else:
                    raise Exception(f"No se pudo restablecer la conexión después de {max_retries} intentos")