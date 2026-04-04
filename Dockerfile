# Dockerfile para Railway
# Sirve la API FastAPI + archivos estaticos del dashboard
FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema para lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python
COPY requirements.txt requirements_api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_api.txt

# Copiar codigo
COPY . .

# Crear directorio de datos
RUN mkdir -p data

# Correr pipeline inicial al buildear (opcional; Railway puede hacerlo en start)
# RUN python scraper_pipeline.py

# Puerto expuesto (Railway lo asigna via $PORT)
EXPOSE 8000

# Comando de inicio
CMD ["python", "api_server.py"]