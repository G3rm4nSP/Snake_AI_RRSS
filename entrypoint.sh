#!/bin/bash
set -e

# Inicia PulseAudio (para SDL2 si tu juego genera sonido)
pulseaudio --start --exit-idle-time=-1

# Inicia Xvfb
Xvfb :99 -screen 0 1280x720x24 &
export DISPLAY=:99

# Delay para asegurar que Xvfb esté listo
sleep 2

# Inicia tu juego Python
python Snake/Snake.py &
GAME_PID=$!

# Espera un poco para que la ventana SDL se abra
sleep 2

# Transmite video + audio por RTMP
# Aquí mezclamos la pantalla (:99) + un archivo de audio de fondo
ffmpeg -y \
    -f x11grab -r 30 -s 1280x720 -i :99 \
    -i Snake/assets/music.mp3 \
    -c:v libx264 -preset veryfast -pix_fmt yuv420p \
    -c:a aac -b:a 128k \
    -shortest \
    -f flv "$RTMP_URL"

# Espera a que el juego termine
wait $GAME_PID
