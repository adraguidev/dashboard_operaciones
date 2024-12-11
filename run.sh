#!/bin/bash
export STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
export STREAMLIT_SERVER_ADDRESS=localhost
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ENABLE_CORS=false
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Limpiar cache
rm -rf ~/.streamlit/cache

# Iniciar con configuración optimizada
streamlit run dashboard.py \
    --server.maxUploadSize=200 \
    --server.enableCORS=false \
    --server.enableXsrfProtection=true \
    --server.maxMessageSize=200 \
    --browser.gatherUsageStats=false \
    --runner.magicEnabled=false \
    --runner.fastRerenderEnabled=false 