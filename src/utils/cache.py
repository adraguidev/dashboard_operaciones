from functools import lru_cache
import streamlit as st

def smart_cache(ttl_seconds=3600):
    """Cache decorator que combina st.cache y lru_cache"""
    def decorator(func):
        @st.cache_data(ttl=ttl_seconds)
        @lru_cache(maxsize=128)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator 