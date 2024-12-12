FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt packages.txt ./

RUN if [ -f "packages.txt" ]; then \
    apt-get update && \
    cat packages.txt | xargs apt-get install -y && \
    rm -rf /var/lib/apt/lists/*; \
    fi

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_SERVER_ADDRESS=dashboardusm.tech \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_RUN_ON_SAVE=true

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

CMD ["streamlit", "run", "dashboard.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--browser.serverAddress=dashboardusm.tech", \
     "--server.enableCORS=true", \
     "--server.enableXsrfProtection=false", \
     "--server.headless=true", \
     "--server.runOnSave=true"]
