FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Instala dependencias de Python, X11, SDL2, FFmpeg y PulseAudio
RUN apt-get update && apt-get install -y \
    python3-dev \
    ffmpeg \
    xvfb \
    pulseaudio \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Crea un usuario no root
RUN useradd -m -u 1000 appuser

# Configura PulseAudio para el usuario no root
RUN mkdir -p /run/pulse && \
    chown -R appuser:appuser /run/pulse

WORKDIR /app

# Instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el proyecto
COPY . .

# Da permisos al entrypoint
RUN chmod +x /app/entrypoint.sh

# Cambia al usuario no root
USER appuser

# Exponemos un puerto (opcional, no estrictamente necesario para RTMP)
EXPOSE 8888

# Entrypoint
CMD ["/app/entrypoint.sh"]

