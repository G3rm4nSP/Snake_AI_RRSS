#!/bin/bash
set -e

# PulseAudio
pulseaudio --start --exit-idle-time=-1
pactl load-module module-null-sink sink_name=stream_sink sink_properties=device.description=StreamSink
pactl set-default-sink stream_sink

# Xvfb
Xvfb :99 -screen 0 1280x720x24 &
export DISPLAY=:99

# Esperar un poco más para asegurar que Xvfb esté listo
sleep 5

# Juego
python Snake/Snake.py &
GAME_PID=$!

# Esperar a que SDL abra ventana (aumentar un poco)
sleep 5

# Streaming con resolución correcta
ffmpeg -y \
  -f x11grab -r 30 -s 1280x720 -i :99 \
  -f pulse -i stream_sink.monitor \
  -c:v libx264 -preset veryfast -pix_fmt yuv420p \
  -c:a aac -b:a 128k \
  -f flv "$RTMP_URL"

# Esperar al juego
wait $GAME_PID
