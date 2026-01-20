# GRABACIÓN AUTOMÁTICA INTEGRADA

## ✅ Instalación (Una sola vez)

```bash
pip install opencv-python
```

## 🎮 Cómo Usar

### En Snake.py - Variable de Control

En la parte superior de `Snake.py`, hay una variable:

```python
GRABACION = True  # Cambiar a False para desactivar
```

### Comportamiento Automático

Cuando ejecutas `python Snake/Snake.py`:

1. **Si GRABACION = True**:
   - Se inicia automáticamente la grabación
   - Cada partida se captura en buffer
   - **En derrota**: Guarda últimos 10 segundos
   - **En victoria**: Guarda video completo a 2x velocidad

2. **Si GRABACION = False**:
   - No se graba nada
   - El juego funciona normal sin overhead

### Dónde se guardan los videos

```
proyecto/
└── videos/
    ├── 2025-01-20_14-30-45_game1_loss.mp4
    ├── 2025-01-20_14-35-20_game2_win_fullgame.mp4
    └── ...
```

### Ver videos grabados

```bash
# Ver resumen de videos
python pruebas/manager.py summary

# Ver solo derrotas
python pruebas/manager.py losses

# Ver solo victorias
python pruebas/manager.py wins
```

## 📋 Configuración (Opcional)

En `pruebas/config.py`, puedes personalizar:

```python
BUFFER_SECONDS = 15        # Segundos a mantener en buffer
LOSS_VIDEO_SECONDS = 10    # Segundos a grabar en derrota
WIN_VIDEO_SPEED = 2        # Velocidad en victoria (2 = doble velocidad)
```

## 🎬 Ejemplo

```bash
# 1. Ejecutar el juego (grabación automática si GRABACION = True)
python Snake/Snake.py

# 2. Dejar que la IA juegue varias partidas
# (pierde algunas, gana otras)

# 3. Ver videos guardados
python pruebas/manager.py summary

# 4. Abrir los videos en reproductor
# Windows: videos/2025-01-20_*.mp4
```

## ⚠️ Solución de Problemas

### "No module named 'cv2'"
```bash
pip install opencv-python
```

### Los videos no se guardan
1. Verifica que `GRABACION = True`
2. Verifica que `pip install opencv-python` fue exitosa
3. Revisa que la carpeta `videos/` existe y es escribible

### Los videos salen en blanco
```python
# En Snake.py, cerca de pygame.display.flip(), 
# cambiar de:
recorder.add_frame(pygame.surfarray.array3d(pantalla))

# A:
capturer.capture_from_surface(pantalla)
```

## 💡 Tips

- Los videos tienen **0% impacto** en FPS (runs en thread separado)
- Buffer circular eficiente (solo ~100-200 MB)
- Nombres únicos no sobrescriben
- Perfectos para debuguear: ¿Por qué perdió? Ver los últimos 10s

## 📚 Más Info

Ver: `pruebas/README.md` para documentación completa
