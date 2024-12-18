import streamlit as st
from typing import Any, Dict, Optional
import json

class StateManager:
    """
    Maneja el estado global de la aplicación de manera eficiente.
    """
    
    @staticmethod
    def init_session_state():
        """
        Inicializa el estado de la sesión con valores por defecto.
        """
        default_states = {
            'current_module': None,
            'selected_filters': {},
            'last_update': None,
            'cached_data': {},
            'ui_preferences': {
                'theme': 'light',
                'table_height': 400,
                'chart_style': 'modern'
            }
        }
        
        for key, default_value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = default_value

    @staticmethod
    def get_state(key: str, default: Any = None) -> Any:
        """
        Obtiene un valor del estado de manera segura.
        """
        return st.session_state.get(key, default)

    @staticmethod
    def set_state(key: str, value: Any):
        """
        Establece un valor en el estado.
        """
        st.session_state[key] = value

    @staticmethod
    def update_filters(new_filters: Dict):
        """
        Actualiza los filtros manteniendo el historial.
        """
        current_filters = st.session_state.get('selected_filters', {})
        current_filters.update(new_filters)
        st.session_state['selected_filters'] = current_filters

    @staticmethod
    def clear_filters():
        """
        Limpia todos los filtros aplicados.
        """
        st.session_state['selected_filters'] = {}

    @staticmethod
    def save_ui_preference(key: str, value: Any):
        """
        Guarda una preferencia de UI.
        """
        if 'ui_preferences' not in st.session_state:
            st.session_state['ui_preferences'] = {}
        st.session_state['ui_preferences'][key] = value

    @staticmethod
    def get_ui_preference(key: str, default: Any = None) -> Any:
        """
        Obtiene una preferencia de UI.
        """
        if 'ui_preferences' not in st.session_state:
            return default
        return st.session_state['ui_preferences'].get(key, default)

    @staticmethod
    def cache_data(key: str, data: Any):
        """
        Cachea datos para uso posterior.
        """
        if 'cached_data' not in st.session_state:
            st.session_state['cached_data'] = {}
        st.session_state['cached_data'][key] = data

    @staticmethod
    def get_cached_data(key: str, default: Any = None) -> Any:
        """
        Obtiene datos cacheados.
        """
        if 'cached_data' not in st.session_state:
            return default
        return st.session_state['cached_data'].get(key, default)

    @staticmethod
    def clear_cache():
        """
        Limpia todos los datos cacheados.
        """
        st.session_state['cached_data'] = {} 