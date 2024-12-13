#!/bin/bash

echo "🔄 Iniciando monitoreo de cambios..."

while true; do
    # Monitorear cambios en archivos Python y configuración
    inotifywait -r -e modify,create,delete,move ./**/*.py ./**/*.yaml ./**/*.json ./**/*.toml

    echo "📝 Cambios detectados, reiniciando contenedor..."
    
    # Reiniciar solo el contenedor de Streamlit
    docker-compose restart streamlit

    echo "✅ Contenedor reiniciado"
done 