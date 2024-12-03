import pandas as pd
from datetime import datetime, timedelta

def process_date_columns(data):
    """
    Procesar y validar columnas de fecha.
    """
    date_columns = ['FechaExpendiente', 'FechaPre', 'FECHA DE TRABAJO']
    
    for col in date_columns:
        if col in data.columns:
            data[col] = pd.to_datetime(data[col], errors='coerce')
    
    return data

def filter_date_range(data, start_date=None, end_date=None, date_column='FechaExpendiente'):
    """
    Filtrar datos por rango de fechas.
    """
    if start_date:
        data = data[data[date_column] >= start_date]
    if end_date:
        data = data[data[date_column] <= end_date]
    return data

def calculate_processing_times(data):
    """
    Calcular tiempos de procesamiento entre fechas.
    """
    if 'FechaExpendiente' in data.columns and 'FechaPre' in data.columns:
        data['TiempoProcesamiento'] = (data['FechaPre'] - data['FechaExpendiente']).dt.days
    return data

def get_evaluator_statistics(data, evaluator):
    """
    Obtener estadísticas por evaluador.
    """
    evaluator_data = data[data['EVALASIGN'] == evaluator]
    
    stats = {
        'total_expedientes': len(evaluator_data),
        'pendientes': len(evaluator_data[evaluator_data['Evaluado'] == 'NO']),
        'completados': len(evaluator_data[evaluator_data['Evaluado'] == 'SI']),
        'tiempo_promedio': evaluator_data['TiempoProcesamiento'].mean() if 'TiempoProcesamiento' in evaluator_data.columns else None
    }
    
    return stats

def get_module_statistics(data):
    """
    Obtener estadísticas generales del módulo.
    """
    stats = {
        'total_expedientes': len(data),
        'total_pendientes': len(data[data['Evaluado'] == 'NO']),
        'total_completados': len(data[data['Evaluado'] == 'SI']),
        'expedientes_sin_asignar': len(data[data['EVALASIGN'].isna()]),
        'tiempo_promedio_general': data['TiempoProcesamiento'].mean() if 'TiempoProcesamiento' in data.columns else None
    }
    
    return stats

def calculate_trends(data, column, window=7):
    """
    Calcular tendencias en los datos.
    """
    if len(data) < window:
        return None
        
    rolling_mean = data[column].rolling(window=window).mean()
    trend = rolling_mean.iloc[-1] - rolling_mean.iloc[0]
    
    return {
        'tendencia': trend,
        'direccion': 'aumentando' if trend > 0 else 'disminuyendo' if trend < 0 else 'estable',
        'porcentaje_cambio': (trend / rolling_mean.iloc[0] * 100) if rolling_mean.iloc[0] != 0 else 0
    }

def validate_data_integrity(data):
    """
    Validar integridad de los datos.
    """
    validation_results = {
        'missing_dates': data['FechaExpendiente'].isna().sum(),
        'invalid_dates': len(data[data['FechaExpendiente'] > data['FechaPre']]) if 'FechaPre' in data.columns else 0,
        'missing_evaluators': data['EVALASIGN'].isna().sum(),
        'data_completeness': (1 - data.isna().sum() / len(data)) * 100
    }
    
    return validation_results 