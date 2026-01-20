"""
Sistema de grabación de video para Snake Game
Captura derrotas (últimos N segundos) y victorias (partida completa)
"""

import cv2
import numpy as np
from collections import deque
from threading import Thread
from queue import Queue
import os
from datetime import datetime

# ================ CONFIGURACIÓN ================
LOSS_VIDEO_SECONDS = 10  # Segundos a capturar en derrota (últimos N segundos)
FPS_RECORDING = 20  # Fotogramas por segundo
OUTPUT_DIR = "videos"  # Carpeta de salida


class VideoRecorder:
    """Grabador de video con buffer circular para derrotas"""
    
    def __init__(self, fps=FPS_RECORDING, buffer_seconds=LOSS_VIDEO_SECONDS, output_dir=OUTPUT_DIR):
        self.fps = fps
        self.buffer_seconds = buffer_seconds
        self.output_dir = output_dir
        self.frame_queue = Queue(maxsize=100)
        self.frame_buffer = deque(maxlen=fps * buffer_seconds)
        self.recording_win = False
        self.win_frames = []
        self.game_number = 1
        self.writer_thread = None
        self.is_writing = False
        
        os.makedirs(output_dir, exist_ok=True)
    
    def add_frame(self, frame):
        """Agregar frame al buffer"""
        if frame is None:
            return
        
        # Frame ya viene en BGR desde setup_recorder, solo copiar
        frame_copy = frame.copy()
        
        # Agregar al buffer de derrotas
        self.frame_buffer.append(frame_copy)
        
        # Agregar a victorias si estamos grabando
        if self.recording_win:
            self.win_frames.append(frame_copy)
    
    def start_game(self):
        """Inicia grabación de una nueva partida"""
        self.win_frames = []
        self.recording_win = True
    
    def on_loss(self):
        """Guardar video de derrota (últimos N segundos del buffer)"""
        if not self.frame_buffer:
            return
        
        self.recording_win = False
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.output_dir, f"{timestamp}_game{self.game_number}_loss.mp4")
        
        # Iniciar escritura en thread separado (NO bloquea el juego)
        frames_copy = list(self.frame_buffer)
        thread = Thread(target=self._write_video, args=(frames_copy, filename, 1.0), daemon=True)
        thread.start()
        self.game_number += 1
    
    def on_win(self):
        """Guardar video de victoria (partida completa a 2x velocidad)"""
        if not self.win_frames:
            return
        
        self.recording_win = False
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.output_dir, f"{timestamp}_game{self.game_number}_win_fullgame.mp4")
        
        # Iniciar escritura en thread separado (NO bloquea el juego)
        frames_copy = list(self.win_frames)
        thread = Thread(target=self._write_video, args=(frames_copy, filename, 2.0), daemon=True)
        thread.start()
        self.game_number += 1
    
    def _write_video(self, frames, filename, speed=1.0):
        """Escribir video a archivo en thread separado (NO bloquea)"""
        if not frames or len(frames) == 0:
            return
        
        try:
            # Obtener resolución del primer frame
            h, w = frames[0].shape[:2]
            
            # Crear video writer con codec MP4
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps_output = int(self.fps * speed)
            out = cv2.VideoWriter(filename, fourcc, fps_output, (w, h))
            
            # Escribir frames
            for frame in frames:
                if frame.shape[:2] != (h, w):
                    frame = cv2.resize(frame, (w, h))
                out.write(frame)
            
            out.release()
            print(f"▶ Video grabado: {os.path.basename(filename)}")
        except Exception as e:
            print(f"✗ Error grabando video: {e}")


def init_recorder(fps=FPS_RECORDING, buffer_seconds=LOSS_VIDEO_SECONDS, output_dir=OUTPUT_DIR):
    """Inicializar grabador"""
    return VideoRecorder(fps=fps, buffer_seconds=buffer_seconds, output_dir=output_dir)


def setup_recorder(screen_surface, recorder):
    """Configurar capturador de frames desde pygame"""
    
    def frame_capturer():
        """Capturar frames de pygame en background"""
        import pygame
        while True:
            try:
                # Capturar array del surface (width, height, 3)
                surface_array = pygame.surfarray.array3d(screen_surface)
                
                # Transponer a (height, width, 3) y hacer copia contiguous
                frame = np.transpose(surface_array, (1, 0, 2)).copy()
                
                # Asegurar que es contiguous en memoria
                frame = np.ascontiguousarray(frame)
                
                # Convertir RGB a BGR para OpenCV
                frame = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_RGB2BGR)
                
                recorder.add_frame(frame)
            except:
                pass
    
    # Iniciar captura en thread daemon
    capture_thread = Thread(target=frame_capturer, daemon=True)
    capture_thread.start()
    
    return recorder
