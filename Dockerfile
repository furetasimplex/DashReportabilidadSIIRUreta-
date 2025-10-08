# Imagen base ligera de Python
FROM python:3.13-slim

# Evita prompts interactivos
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y curl gnupg apt-transport-https

# Agrega el repo de Microsoft y el driver ODBC 18
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copia el proyecto
WORKDIR /app
COPY . .

# Instala dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Expón el puerto (Render lo asignará automáticamente)
EXPOSE 10000

# Comando de ejecución
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:10000"]
