import psutil
import platform
import os
import time
from datetime import datetime, timedelta
import pymongo
from typing import Dict, List, Any
import logging
import json

class SystemMonitor:
    def __init__(self, db_connection):
        self.db = db_connection
        self.start_time = datetime.now()
        
        # Configurar logging
        logging.basicConfig(
            filename='system.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Obtiene métricas del sistema en tiempo real."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_usage": cpu_percent,
                "memory_used": memory.used / (1024 * 1024 * 1024),  # GB
                "memory_total": memory.total / (1024 * 1024 * 1024),  # GB
                "memory_percent": memory.percent,
                "disk_used": disk.used / (1024 * 1024 * 1024),  # GB
                "disk_total": disk.total / (1024 * 1024 * 1024),  # GB
                "disk_percent": disk.percent,
                "timestamp": datetime.now()
            }
        except Exception as e:
            logging.error(f"Error al obtener métricas del sistema: {str(e)}")
            return {}
    
    def get_mongodb_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de MongoDB."""
        try:
            stats = self.db.command("serverStatus")
            return {
                "connections": stats["connections"],
                "opcounters": stats["opcounters"],
                "mem_usage": stats["mem"]["resident"],
                "timestamp": datetime.now()
            }
        except Exception as e:
            logging.error(f"Error al obtener estadísticas de MongoDB: {str(e)}")
            return {}
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Obtiene estadísticas de una colección específica."""
        try:
            stats = self.db.command("collStats", collection_name)
            return {
                "size": stats["size"] / (1024 * 1024),  # MB
                "count": stats["count"],
                "avg_obj_size": stats.get("avgObjSize", 0) / 1024,  # KB
                "storage_size": stats["storageSize"] / (1024 * 1024),  # MB
                "indexes": len(stats["indexSizes"]),
                "timestamp": datetime.now()
            }
        except Exception as e:
            logging.error(f"Error al obtener estadísticas de la colección {collection_name}: {str(e)}")
            return {}
    
    def get_system_logs(self, log_type: str = None, module: str = None, 
                       start_date: datetime = None, end_date: datetime = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene logs del sistema con filtros opcionales."""
        try:
            query = {}
            if log_type and log_type != "Todos":
                query["level"] = log_type
            if module and module != "Todos":
                query["module"] = module
            if start_date:
                query["timestamp"] = {"$gte": start_date}
            if end_date:
                if "timestamp" in query:
                    query["timestamp"]["$lte"] = end_date
                else:
                    query["timestamp"] = {"$lte": end_date}
            
            logs = list(self.db.system_logs.find(query).sort("timestamp", -1).limit(limit))
            return logs
        except Exception as e:
            logging.error(f"Error al obtener logs del sistema: {str(e)}")
            return []
    
    def log_event(self, level: str, message: str, module: str = None) -> None:
        """Registra un evento en los logs del sistema."""
        try:
            log_entry = {
                "timestamp": datetime.now(),
                "level": level,
                "message": message,
                "module": module
            }
            self.db.system_logs.insert_one(log_entry)
            logging.log(
                getattr(logging, level.upper(), logging.INFO),
                f"[{module or 'System'}] {message}"
            )
        except Exception as e:
            logging.error(f"Error al registrar evento: {str(e)}")
    
    def clean_old_data(self, collection_name: str, days: int) -> int:
        """Limpia datos antiguos de una colección."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            result = self.db[collection_name].delete_many({"timestamp": {"$lt": cutoff_date}})
            return result.deleted_count
        except Exception as e:
            logging.error(f"Error al limpiar datos antiguos de {collection_name}: {str(e)}")
            return 0
    
    def get_uptime(self) -> str:
        """Obtiene el tiempo de actividad del sistema."""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        return f"{days}d {hours}h {minutes}m"
    
    def optimize_collection(self, collection_name: str) -> bool:
        """Optimiza una colección de MongoDB."""
        try:
            self.db.command("compact", collection_name)
            return True
        except Exception as e:
            logging.error(f"Error al optimizar la colección {collection_name}: {str(e)}")
            return False
    
    def backup_config(self, backup_path: str = "backups") -> str:
        """Realiza una copia de seguridad de la configuración del sistema."""
        try:
            if not os.path.exists(backup_path):
                os.makedirs(backup_path)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_path, f"config_backup_{timestamp}.json")
            
            config = {
                "system_info": {
                    "platform": platform.platform(),
                    "python_version": platform.python_version(),
                    "start_time": self.start_time.isoformat()
                },
                "mongodb_config": self.db.client.options,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(backup_file, 'w') as f:
                json.dump(config, f, indent=2, default=str)
            
            return backup_file
        except Exception as e:
            logging.error(f"Error al realizar backup de configuración: {str(e)}")
            return ""