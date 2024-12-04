from typing import List, Dict
import pandas as pd

class DataValidator:
    @staticmethod
    def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> bool:
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Columnas faltantes: {missing_columns}")
        return True 