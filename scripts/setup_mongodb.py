from pymongo import MongoClient, ASCENDING
from src.utils.database import get_mongodb_connection
from config.settings import MONGODB_COLLECTIONS

def setup_mongodb_indexes():
    """Configura índices necesarios en MongoDB."""
    client = get_mongodb_connection()
    db = client['migraciones_db']
    
    try:
        # Índices para colecciones principales
        for collection_name in MONGODB_COLLECTIONS.values():
            collection = db[collection_name]
            collection.create_index([("FechaPre", ASCENDING)])
            collection.create_index([("FECHA DE TRABAJO", ASCENDING)])
            collection.create_index([("NumeroTramite", ASCENDING)])
            print(f"✅ Índices creados para {collection_name}")

        # Índices para rankings
        rankings = db.rankings
        rankings.create_index([
            ("modulo", ASCENDING),
            ("fecha", ASCENDING)
        ], unique=True)
        print("✅ Índices creados para rankings")

    except Exception as e:
        print(f"❌ Error creando índices: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    setup_mongodb_indexes() 