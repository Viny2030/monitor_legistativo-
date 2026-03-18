FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Asegura que el CSV esté accesible
RUN if [ ! -f nomina_diputados.csv ]; then \
      echo "Nombre,Distrito,Bloque" > nomina_diputados.csv; \
    fi

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]