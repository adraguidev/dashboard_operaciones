import logging
import streamlit as st
from datetime import datetime

class StreamlitHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                st.error(msg)
            elif record.levelno >= logging.WARNING:
                st.warning(msg)
            elif record.levelno >= logging.INFO:
                st.info(msg)
        except Exception:
            self.handleError(record)

def setup_logging():
    logger = logging.getLogger('streamlit_app')
    logger.setLevel(logging.INFO)
    
    # Handler para Streamlit
    st_handler = StreamlitHandler()
    st_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    st_handler.setFormatter(formatter)
    logger.addHandler(st_handler)
    
    return logger

# Crear logger global
logger = setup_logging() 