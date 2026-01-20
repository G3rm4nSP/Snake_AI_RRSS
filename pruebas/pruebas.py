"""
Grabación de videos para Snake Game
Captura derrotas (últimos 10s) y victorias (partida completa a 2x)
"""

import cv2
import numpy as np
from collections import deque
from threading import Thread
import os
from datetime import datetime

# ============= CONFIGURACIÓN =============
BUFFER_SECONDS = 10  # Segundos para derrota
FPS = 20
OUTPUT_DIR = "videos"


class Grabador:
    def __init__(self):
        self.buffer_frames = deque(maxlen=FPS * BUFFER_SECONDS)
        self.frames_victoria = []
        self.grabando_victoria = False
        self.numero_partida = 1
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    def agregar_frame(self, frame):
        """Agregar un frame al buffer"""
        if frame is None:
            return
        
        # Frame ya viene en BGR desde pygame
        self.buffer_frames.append(frame.copy())
        
        if self.grabando_victoria:
            self.frames_victoria.append(frame.copy())
    
    def iniciar_partida(self):
        """Comenzar grabación de nueva partida"""
        self.frames_victoria = []
        self.grabando_victoria = True
    
    def guardar_derrota(self):
        """Guardar video de derrota"""
        if not self.buffer_frames:
            return
        
        self.grabando_victoria = False
        frames = list(self.buffer_frames)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archivo = f"{OUTPUT_DIR}/{timestamp}_game{self.numero_partida}_loss.mp4"
        
        # Guardar en thread separado
        Thread(
            target=self._escribir_video,
            args=(frames, archivo, 1.0),
            daemon=True
        ).start()
        
        self.numero_partida += 1
    
    def guardar_victoria(self):
        """Guardar video de victoria"""
        if not self.frames_victoria:
            return
        
        self.grabando_victoria = False
        frames = list(self.frames_victoria)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archivo = f"{OUTPUT_DIR}/{timestamp}_game{self.numero_partida}_win_fullgame.mp4"
        
        # Guardar en thread separado a 2x velocidad
        Thread(
            target=self._escribir_video,
            args=(frames, archivo, 2.0),
            daemon=True
        ).start()
        
        self.numero_partida += 1
    
    def _escribir_video(self, frames, archivo, velocidad):
        """Escribir video a archivo (corre en thread separado)"""
        if not frames:
            return
        
        try:
            h, w = frames[0].shape[:2]
            fps_salida = int(FPS * velocidad)
            
            writer = cv2.VideoWriter(
                archivo,
                cv2.VideoWriter_fourcc(*'mp4v'),
                fps_salida,
                (w, h)
            )
            
            for frame in frames:
                if frame.shape[:2] != (h, w):
                    frame = cv2.resize(frame, (w, h))
                writer.write(frame)
            
            writer.release()
            print(f"✓ Video: {os.path.basename(archivo)}")
        except Exception as e:
            print(f"✗ Error: {e}")


def init_recorder(fps=FPS, buffer_seconds=BUFFER_SECONDS, output_dir=OUTPUT_DIR):
    """Inicializar grabador"""
    return Grabador()


def setup_recorder(pantalla, grabador):
    """Capturar frames desde pygame en background"""
    
    def capturador():
        import pygame
        
        while True:
            try:
                # Obtener array de pygame (width, height, 3)
                arr = pygame.surfarray.array3d(pantalla)
                
                # Copiar y transponer a (height, width, 3)
                frame = np.transpose(arr, (1, 0, 2)).copy()
                frame = np.ascontiguousarray(frame)
                
                # RGB a BGR
                frame = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_RGB2BGR)
                
                grabador.agregar_frame(frame)
            except:
                pass
    
    # Iniciar en thread daemon
    Thread(target=capturador, daemon=True).start()
    
    return grabador
