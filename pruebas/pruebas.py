"""
Grabación de videos para Snake Game - Sistema Asincrónico
Graba toda la partida pero:
  - Derrota: guarda solo últimos 10 segundos
  - Victoria: guarda partida completa
Ejecuta grabación en thread separado para no bloquear el juego
"""

import cv2
import numpy as np
from collections import deque
from threading import Thread, Lock
import os
from datetime import datetime
import time
import queue

# ============= CONFIGURACIÓN =============
BUFFER_SECONDS = 10  # Segundos de buffer para derrotas
FPS = 20
OUTPUT_DIR = "videos"


class Grabador:
    def __init__(self):
        """Inicializar grabador con buffer circular para derrotas"""
        self.buffer_frames = deque(maxlen=FPS * BUFFER_SECONDS)
        self.frames_partida = []  # Buffer completo de la partida actual
        self.grabando = False
        self.lock = Lock()
        self.cola_guardado = queue.Queue()  # Cola asincrónica de guardado
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Iniciar worker thread para guardar videos
        self._iniciar_worker_guardado()
    
    def _iniciar_worker_guardado(self):
        """Inicia thread que guarda videos de forma asincrónica"""
        def worker():
            while True:
                try:
                    tarea = self.cola_guardado.get(timeout=1)
                    if tarea is None:
                        break
                    frames, archivo, resultado_partida = tarea
                    self._escribir_video(frames, archivo, resultado_partida)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"✗ Error en worker de guardado: {e}")
        
        worker_thread = Thread(target=worker, daemon=True)
        worker_thread.start()
    
    def agregar_frame(self, frame_rgb, grabacion_activa):
        """Agregar frame a buffers circular y de partida"""
        if frame_rgb is None or not grabacion_activa:
            return
        
        try:
            with self.lock:
                # Copiar y convertir frame
                frame = frame_rgb.copy()
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Siempre al buffer circular (últimos 10s)
                self.buffer_frames.append(frame)
                
                # Si estamos grabando, también al buffer de partida
                if self.grabando:
                    self.frames_partida.append(frame)
        except Exception as e:
            pass
    
    def iniciar_partida(self):
        """Comienza grabación de una nueva partida"""
        with self.lock:
            self.frames_partida = []
            self.grabando = True
    
    def guardar_derrota(self):
        """Encola guardado de derrota (últimos 10 segundos)"""
        if not self.grabando:
            return
        
        with self.lock:
            self.grabando = False
            frames = list(self.buffer_frames)  # Últimos 10s del buffer circular
        
        # Filtrar frames válidos (no nulos)
        frames_validos = [f for f in frames if f is not None and f.size > 0]
        
        # Requiere mínimo 5 frames para hacer video
        if not frames_validos or len(frames_validos) < 5:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archivo = f"{OUTPUT_DIR}/{timestamp}_loss.mp4"
        
        # Encolar para guardado asincrónico
        self.cola_guardado.put((frames_validos, archivo, "loss"))
    
    def guardar_victoria(self):
        """Encola guardado de victoria (partida completa)"""
        with self.lock:
            frames = list(self.frames_partida)  # Toda la partida
            self.grabando = False
        
        # Filtrar frames válidos (no nulos)
        frames_validos = [f for f in frames if f is not None and f.size > 0]
        
        # Requiere mínimo 5 frames para hacer video
        if not frames_validos or len(frames_validos) < 5:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archivo = f"{OUTPUT_DIR}/{timestamp}_win.mp4"
        
        # Encolar para guardado asincrónico
        self.cola_guardado.put((frames_validos, archivo, "win"))
    
    def _escribir_video(self, frames, archivo, resultado_partida):
        """Escribir video a archivo (ejecuta en thread worker)"""
        if not frames or len(frames) == 0:
            return
        
        try:
            # Filtrar frames nulos una vez más por si acaso
            frames_limpios = [f for f in frames if f is not None and f.size > 0]
            if len(frames_limpios) < 5:
                return
            
            primer_frame = frames_limpios[0]
            if primer_frame is None or len(primer_frame.shape) != 3:
                raise Exception("Frame inválido")
            
            h, w = primer_frame.shape[:2]
            
            # Asegurar múltiplos de 2 (requerido por codec)
            if h % 2 != 0:
                h -= 1
            if w % 2 != 0:
                w -= 1
            
            # FPS según tipo de partida
            fps_salida = FPS if resultado_partida == "loss" else FPS
            
            # Usar codec MJPG (compatible)
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            archivo_avi = archivo.replace('.mp4', '.avi')
            writer = cv2.VideoWriter(archivo_avi, fourcc, fps_salida, (w, h))
            
            if not writer.isOpened():
                raise Exception("No se pudo abrir VideoWriter")
            
            frames_escritos = 0
            for frame in frames_limpios:
                try:
                    if frame is None or frame.size == 0:
                        continue
                    
                    if frame.dtype != np.uint8:
                        frame = frame.astype(np.uint8)
                    
                    if frame.shape[0] != h or frame.shape[1] != w:
                        frame = cv2.resize(frame, (w, h))
                    
                    if writer.write(frame):
                        frames_escritos += 1
                except:
                    continue
            
            writer.release()
            
            if frames_escritos > 0:
                print(f"[OK] Video {resultado_partida}: {os.path.basename(archivo_avi)} ({frames_escritos} frames @ {fps_salida} fps)")
            else:
                # Si no se escribió nada, no mostrar error
                pass
        
        except Exception as e:
            # Solo mostrar si es un error real
            if "No se escribió ningún frame" not in str(e):
                print(f"[ERROR] Escribiendo video: {e}")


def init_recorder(fps=FPS, buffer_seconds=BUFFER_SECONDS, output_dir=OUTPUT_DIR):
    """Inicializar grabador"""
    return Grabador()


def setup_recorder(pantalla, grabador):
    """Capturar frames desde pygame en thread separado"""
    
    def capturador():
        import pygame
        
        while True:
            try:
                # Acceso directo a pixels del pygame surface
                pixels = pygame.surfarray.array3d(pantalla)
                
                # Transponer de (width, height, 3) a (height, width, 3)
                frame = np.transpose(pixels, (1, 0, 2))
                frame = np.ascontiguousarray(frame)
                frame = frame.astype(np.uint8)
                
                # Agregar frame (grabacion_activa se pasa desde Snake.py)
                grabador.agregar_frame(frame, True)
                
                time.sleep(1.0 / FPS)
            except Exception as e:
                pass
    
    capture_thread = Thread(target=capturador, daemon=True)
    capture_thread.start()
    
    return grabador
