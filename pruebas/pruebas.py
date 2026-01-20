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
import time

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
    
    def agregar_frame(self, frame_rgb):
        """Agregar un frame al buffer - recibe RGB desde pygame"""
        if frame_rgb is None:
            return
        
        try:
            # Copiar frame
            frame = frame_rgb.copy()
            
            # Convertir RGB -> BGR para OpenCV
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            # Agregar al buffer circular
            self.buffer_frames.append(frame)
            
            # Agregar a victorias si estamos grabando
            if self.grabando_victoria:
                self.frames_victoria.append(frame)
        except:
            pass
    
    def iniciar_partida(self):
        """Comenzar grabación de nueva partida"""
        self.frames_victoria = []
        self.grabando_victoria = True
    
    def guardar_derrota(self):
        """Guardar video de derrota"""
        if not self.buffer_frames or len(self.buffer_frames) == 0:
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
        if not self.frames_victoria or len(self.frames_victoria) == 0:
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
        if not frames or len(frames) == 0:
            return
        
        try:
            # Validar primer frame
            primer_frame = frames[0]
            if primer_frame is None or len(primer_frame.shape) != 3:
                raise Exception("Frame inválido")
            
            # Obtener dimensiones
            h, w = primer_frame.shape[:2]
            
            # Asegurar que son múltiples de 2 (requerido para codecs)
            if h % 2 != 0:
                h = h - 1
            if w % 2 != 0:
                w = w - 1
            
            # FPS de salida ajustado por velocidad
            fps_salida = int(FPS * velocidad)
            
            # Crear VideoWriter con XVID (más compatible)
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            writer = cv2.VideoWriter(archivo.replace('.mp4', '.avi'), fourcc, fps_salida, (w, h))
            
            if not writer.isOpened():
                raise Exception("No se pudo abrir VideoWriter")
            
            # Escribir cada frame
            frames_escritos = 0
            for frame in frames:
                # Validar y ajustar frame
                if frame is None or frame.size == 0:
                    continue
                
                if frame.dtype != np.uint8:
                    frame = frame.astype(np.uint8)
                
                # Redimensionar si es necesario
                if frame.shape[0] != h or frame.shape[1] != w:
                    frame = cv2.resize(frame, (w, h))
                
                # Escribir
                if writer.write(frame):
                    frames_escritos += 1
            
            writer.release()
            
            if frames_escritos == 0:
                raise Exception("No se escribió ningún frame")
            
            print(f"✓ Video: {os.path.basename(archivo)} ({frames_escritos} frames)")
            
        except Exception as e:
            print(f"✗ Error escribiendo video: {e}")


def init_recorder(fps=FPS, buffer_seconds=BUFFER_SECONDS, output_dir=OUTPUT_DIR):
    """Inicializar grabador"""
    return Grabador()


def setup_recorder(pantalla, grabador):
    """Capturar frames desde pygame en background"""
    
    def capturador():
        import pygame
        
        while True:
            try:
                # Usar pygame.surfarray.array3d para acceso directo
                # array3d devuelve (width, height, 3) en formato RGB
                pixels = pygame.surfarray.array3d(pantalla)
                
                # Transponer de (width, height, 3) a (height, width, 3)
                # Hacer copia contiguous para asegurar compatibilidad
                frame = np.transpose(pixels, (1, 0, 2))
                frame = np.ascontiguousarray(frame)
                
                # Convertir a uint8
                frame = frame.astype(np.uint8)
                
                # Agregar al grabador
                grabador.agregar_frame(frame)
                
            except Exception as e:
                pass
    
    # Iniciar en thread daemon
    capture_thread = Thread(target=capturador, daemon=True)
    capture_thread.start()
    
    return grabador
