# Imagen base liviana con Python 3.13
FROM python:3.13-slim

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Evita prompts interactivos al instalar paquetes
ENV DEBIAN_FRONTEND=noninteractive

# 🔹 Instalar dependencias del sistema necesarias para OpenCV, pyodbc y otras librerías
RUN apt-get update && apt-get install -y \
    build-essential \
    unixodbc-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# 🔹 Copiar los archivos de la aplicación
COPY . .

# 🔹 Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# 🔹 Exponer el puerto que Render espera
EXPOSE 10000

# 🔹 Comando de ejecución (puerto desde variable de entorno PORT)
CMD ["sh", "-c", "gunicorn -w 2 -b 0.0.0.0:${PORT:-10000} wsgi:application"]
