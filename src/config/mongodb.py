from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class MongoDBConfig:
    uri: str
    database: str
    collections: Dict[str, str]
    timeout_ms: int = 5000

    def get_connection_params(self) -> Dict[str, Any]:
        return {
            "host": self.uri,
            "serverSelectionTimeoutMS": self.timeout_ms
        } 