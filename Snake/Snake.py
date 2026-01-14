import pygame
import random
import os
import sys
import colorsys
import math, time
from pygame import gfxdraw



# ================= IA A* =================
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from Player.ai import(
    StarPathfinder,
    StarExtensions,
    Direction,
    Position,
    CellType
)

# TRIGGERS_BOTS
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from Triggers.triggers import trigger_queue, run_triggers

pygame.init()

# ================= CONFIG =================
FPS = 20
VELOCIDAD_BASE = 5
DANO_MINA = 3
TAMAÑO_TABLERO_INICIAL = 10
DEBUG = True  # o False para desactivar debug


VERDE_CLARO = (170, 220, 170)
VERDE_OSCURO = (130, 180, 130)
BORDE_ROJO = (120, 0, 0)
FRUTA_COLOR = (0, 200, 0)
MINA_COLOR = (200, 0, 0)
TEXTO_COLOR = (240, 240, 240)

clock = pygame.time.Clock()
fuente = pygame.font.SysFont("consolas", 22)
fuente_grande = pygame.font.SysFont("consolas", 42)
fuente_console_big = pygame.font.SysFont("consolas", 96)

ANCHO = 380
ALTO = 720

HUD_ALTO = 56
MENU_HEIGHT = 260   # NUEVO: menú abajo
MENU_WIDTH = 0      # ya no se usa lateral


pantalla = pygame.display.set_mode((ANCHO, ALTO))

# Cargar iconos de assets (0.png .. 9.png)
ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
ICON_SIZE = 52
icons = {}
for i in range(0, 10):
    path = os.path.join(ASSETS_DIR, f"{i}.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        icons[i] = pygame.transform.smoothscale(img, (ICON_SIZE, ICON_SIZE))
    except Exception:
        icons[i] = None

# Cargar todas las frutas en un diccionario
NUM_FRUTAS = 12
frutas = {}
for i in range(1, NUM_FRUTAS + 1):
    path = os.path.join(ASSETS_DIR, f"fruta{i}.png")
    try:
        img = pygame.image.load(path).convert_alpha()
        # Escalar la fruta al tamaño que quieras
        frutas[i] = pygame.transform.smoothscale(img, (ICON_SIZE, ICON_SIZE))
    except Exception:
        frutas[i] = None

mina_img = pygame.image.load(os.path.join(ASSETS_DIR, "mina.png")).convert_alpha()

# Inicializar pygame mixer
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
pygame.mixer.music.load(os.path.join(ASSETS_DIR, "music.mp3"))
pygame.mixer.music.play(-1)
# # Ejemplo de efecto
# efecto_click = pygame.mixer.Sound(os.path.join(ASSETS_DIR, "click1.mp3"))
# #efecto_click.play() para que suene

# ================= IA ADAPTADOR =================

class StarAI:
    def __init__(self):
        self.risk = 0
        self.first_move_done = False  # ⚡ variable para controlar el primer movimiento

    def set_difficulty(self, v):
        self.risk = v

    def get_next_move(self, juego):
        cx, cy = juego.casillas_x, juego.casillas_y

        # ⚡ Primer movimiento obligatorio a la izquierda
        if not self.first_move_done:
            self.first_move_done = True
            return Direction.Left.value  # (dx, dy)

        # construir grid
        grid = [[CellType.Empty.value for _ in range(cy)] for _ in range(cx)]

        for x, y in juego.snake.cuerpo[:-1]:
            grid[x][y] = CellType.SnakeBody.value

        for x, y in juego.minas:
            grid[x][y] = CellType.Wall.value

        for x, y in juego.frutas:
            grid[x][y] = CellType.Food.value

        hx, hy = juego.snake.cuerpo[-1]
        tx, ty = juego.snake.cuerpo[0]
        fx, fy = juego.frutas[0] if juego.frutas else (hx, hy)

        path = StarPathfinder.find_path(
            grid,
            Position(hx, hy),
            Position(tx, ty),
            Position(fx, fy),
            juego.snake.cuerpo
        )

        if not path or path == "NOT_FOUND":
            return None

        d = StarExtensions.char_to_direction(path[0])
        return d.value  # (dx, dy)



# ================= UTIL =================
def calcular_tam_casilla(cx, cy):
    available_height = max(ALTO - HUD_ALTO - MENU_HEIGHT, 200)
    available_width = ANCHO
    return min(available_width // cx, available_height // cy)

def hsv_color(h, s=1, v=1):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)

# ================= SNAKE =================
class Snake:
    def __init__(self, cx, cy):
        self.reset(cx, cy)

    def reset(self, cx, cy):
        self.direccion = (1, 0)
        self.longitud = 5
        self.cuerpo = [(cx//2 - i, cy//2) for i in range(self.longitud)]
        self.hue = 0.0

    def cambiar_direccion(self, nueva):
        dx, dy = self.direccion
        ndx, ndy = nueva
        if (dx + ndx, dy + ndy) != (0, 0):
            self.direccion = nueva

    def mover(self):
        if self.longitud <= 0 or not self.cuerpo:
            return False

        x, y = self.cuerpo[-1]
        dx, dy = self.direccion
        self.cuerpo.append((x + dx, y + dy))

        while len(self.cuerpo) > self.longitud:
            self.cuerpo.pop(0)

        return True

    def crecer(self, n=1):
        self.longitud += n

    def reducir(self, n=1):
        self.longitud -= n
        while len(self.cuerpo) > max(self.longitud, 0):
            self.cuerpo.pop(0)

# ================= JUEGO =================
class Juego:
    def __init__(self):
        self.casillas_x = TAMAÑO_TABLERO_INICIAL
        self.casillas_y = TAMAÑO_TABLERO_INICIAL
        self.reset_total()

    def reset_total(self):
        self.casillas_x = TAMAÑO_TABLERO_INICIAL
        self.casillas_y = TAMAÑO_TABLERO_INICIAL
        self.velocidad = VELOCIDAD_BASE
        self.en_juego = False
        self.reset_partida()
        # IA y flags
        self.ai = StarAI()
        # activar IA por defecto
        self.ai_enabled = True
        self.last_human_input = 0
        # colores del tablero (pueden cambiar dinámicamente)
        self.board_light_color = VERDE_CLARO
        self.board_dark_color = VERDE_OSCURO

    def reset_partida(self):
        self.tam = calcular_tam_casilla(self.casillas_x, self.casillas_y)
        self.snake = Snake(self.casillas_x, self.casillas_y)
        self.frutas = []
        self.frutas_ids = {}
        self.minas = []
        self.game_over = False
        self.tiempo_inicio = pygame.time.get_ticks()
        # Garantizar fruta inicial
        try:
            self.ensure_fruit_exists()
        except Exception:
            pass
        # Movimiento independiente del render
        self.move_acc = 0  # acumulador de ms
        self.prev_cuerpo = list(self.snake.cuerpo)
        self.cur_cuerpo = list(self.snake.cuerpo)
        # Resizing (animación al cambiar tamaño de mapa)
        self.resize_active = False
        self.resize_timer = 0
        self.resize_duration = 300  # ms
        self.resize_from = (self.casillas_x, self.casillas_y)
        self.resize_to = (self.casillas_x, self.casillas_y)
        self.prev_tam = self.tam
        self.prev_frutas = list(self.frutas)
        self.cur_frutas = list(self.frutas)
        self.prev_frutas_ids = self.frutas_ids.copy()
        self.cur_frutas_ids = self.frutas_ids.copy()
        self.prev_minas = list(self.minas)
        self.cur_minas = list(self.minas)
        # win / confeti
        self.win_state = False
        self.confeti = []
        self.win_timer = 0
        # estadisticas: conteo de teclas 1..9 y muestras de velocidad
        self.key_counts = {i: 0 for i in range(10)}
        self.speed_samples = []
        self.win_time = None
        # contadores de pickup
        self.frutas_recogidas = 0
        self.minas_activadas = 0
        # pausa / contadores de overlay
        self.paused_elapsed = None  # tiempo en segundos cuando se pausó (victoria/derrota)
        self.win_countdown = None
        self.game_over_countdown = None

    def trigger_game_over(self):
        # Iniciar pantalla de Game Over con cuenta atrás (10s)
        if self.game_over:
            return
        self.game_over = True
        self.game_over_countdown = 10000  # ms cuenta atrás
        self.game_over_start = pygame.time.get_ticks()
        # almacenar tiempo final
        self.game_over_time = pygame.time.get_ticks()
        # pausar tiempo jugado
        if self.paused_elapsed is None:
            self.paused_elapsed = (self.game_over_time - self.tiempo_inicio) / 1000.0
        # (no learning) eliminar lógica de aprendizaje para mantener solo algoritmo

    def tiempo_vivo(self):
        # Si se pausó por victoria/derrota devolver el tiempo congelado
        if self.paused_elapsed is not None:
            return float(self.paused_elapsed)
        if not self.en_juego:
            return 0
        return (pygame.time.get_ticks() - self.tiempo_inicio) / 1000

    def pos_libre(self):
        while True:
            p = (random.randint(0, self.casillas_x - 1),
                 random.randint(0, self.casillas_y - 1))
            if p not in self.snake.cuerpo:
                return p

    def randomize_board_colors(self):
        # elegir un matiz aleatorio y crear dos tonos (claro / oscuro)
        h = random.random()
        # tonos con saturación y valores distintos
        try:
            light = hsv_color(h, 0.35, 0.98)
            dark = hsv_color(h, 0.4, 0.65)
        except Exception:
            light, dark = VERDE_CLARO, VERDE_OSCURO
        self.board_light_color = light
        self.board_dark_color = dark

    def _maybe_randomize_on_growth(self, prev_len):
        try:
            new = self.snake.longitud
            # si cruzamos un múltiplo de 10
            if new // 10 > (prev_len // 10):
                self.randomize_board_colors()
        except Exception:
            pass

    def ensure_fruit_exists(self):
        # Garantizar al menos una fruta en el mapa.
        # Intentar colocar en casilla libre que NO sea mina; solo si no hay huecos, permitir sobreponer a mina.
        if getattr(self, 'frutas', None) is None:
            self.frutas = []
        if len(self.frutas) > 0:
            return

        all_pos = [(x, y) for x in range(self.casillas_x) for y in range(self.casillas_y)]
        forbidden = set(self.snake.cuerpo)
        # opciones que no sean minas
        options = [p for p in all_pos if p not in forbidden and p not in set(self.minas)]
        if options:
            pos = random.choice(options)
            self.frutas.append(pos)
            self.frutas_ids[pos] = random.randint(1, NUM_FRUTAS)
            return

        # si no hay opciones sin minas, permitir sobreponer a mina (pero no al cuerpo)
        options2 = [p for p in all_pos if p not in forbidden]
        if options2:
            pos = random.choice(options)
            self.frutas.append(pos)
            self.frutas_ids[pos] = random.randint(1, NUM_FRUTAS)
            return

        # caso extremo: todo ocupado por cuerpo (muy raro) -> no hacemos nada
        return

    def ampliar_mapa(self):
        if self.resize_active:
            return
        # preparar estado previo
        self.prev_cuerpo = list(self.snake.cuerpo)
        self.prev_frutas = list(self.frutas)
        self.prev_minas = list(self.minas)
        self.prev_tam = calcular_tam_casilla(self.casillas_x, self.casillas_y)

        # aplicar cambio lógico inmediatamente (se mostrará interpolado)
        from_x, from_y = self.casillas_x, self.casillas_y
        self.casillas_x += 2
        self.casillas_y += 2
        self.expandir_offsets(self.casillas_x, self.casillas_y)

        self.snake.cuerpo = [(x + 1, y + 1) for x, y in self.snake.cuerpo]
        self.frutas = [(x + 1, y + 1) for x, y in self.frutas]
        self.minas = [(x + 1, y + 1) for x, y in self.minas]
        self.tam = calcular_tam_casilla(self.casillas_x, self.casillas_y)

        self.cur_cuerpo = list(self.snake.cuerpo)
        self.cur_frutas = list(self.frutas)
        self.cur_minas = list(self.minas)

        # activar transición
        self.resize_active = True
        self.resize_timer = 0
        self.resize_from = (from_x, from_y)
        self.resize_to = (self.casillas_x, self.casillas_y)

    def reducir_mapa(self):
        if self.casillas_x <= 10 or self.casillas_y <= 10 or self.resize_active:
            return
        # preparar prev
        self.prev_cuerpo = list(self.snake.cuerpo)
        self.prev_frutas = list(self.frutas)
        self.prev_minas = list(self.minas)
        self.prev_tam = calcular_tam_casilla(self.casillas_x, self.casillas_y)

        from_x, from_y = self.casillas_x, self.casillas_y
        self.casillas_x -= 2
        self.casillas_y -= 2
        self.expandir_offsets(self.casillas_x, self.casillas_y)

        self.snake.cuerpo = [(x - 1, y - 1) for x, y in self.snake.cuerpo
                             if 0 <= x - 1 < self.casillas_x and 0 <= y - 1 < self.casillas_y]
        self.frutas = [(x - 1, y - 1) for x, y in self.frutas
                       if 0 <= x - 1 < self.casillas_x and 0 <= y - 1 < self.casillas_y]
        self.minas = [(x - 1, y - 1) for x, y in self.minas
                      if 0 <= x - 1 < self.casillas_x and 0 <= y - 1 < self.casillas_y]
        self.tam = calcular_tam_casilla(self.casillas_x, self.casillas_y)

        self.cur_cuerpo = list(self.snake.cuerpo)
        self.cur_frutas = list(self.frutas)
        self.cur_minas = list(self.minas)

        self.resize_active = True
        self.resize_timer = 0
        self.resize_from = (from_x, from_y)
        self.resize_to = (self.casillas_x, self.casillas_y)
        try:
            self.ensure_fruit_exists()
        except Exception:
            pass


    def actualizar(self):
        # Ahora el movimiento se controla externamente por un acumulador
        if not self.en_juego or self.game_over:
            return

        return

    def step_move(self):
        # Ejecuta un paso de movimiento y aplica colisiones/crecimiento
        if not self.snake.mover():
            self.trigger_game_over()
            return

        # registrar velocidad actual para estadística
        try:
            self.speed_samples.append(self.velocidad)
        except Exception:
            pass

        cabeza = self.snake.cuerpo[-1]

        if not (0 <= cabeza[0] < self.casillas_x and 0 <= cabeza[1] < self.casillas_y):
            self.trigger_game_over()
            return

        if cabeza in self.snake.cuerpo[:-1]:
            self.trigger_game_over()
            return

        if cabeza in self.frutas:
            # eliminar todas las frutas en esa casilla (por si hay duplicados)
            while cabeza in self.frutas:
                self.frutas.remove(cabeza)
                self.frutas_recogidas += 1
            prev_len = self.snake.longitud
            self.snake.crecer(1)
            try:
                self._maybe_randomize_on_growth(prev_len)
            except Exception:
                pass
            # asegurar nueva fruta
            try:
                self.ensure_fruit_exists()
            except Exception:
                pass

        if cabeza in self.minas:
            while cabeza in self.minas:
                self.minas.remove(cabeza)
                self.minas_activadas += 1
            self.snake.reducir(DANO_MINA)
            if self.snake.longitud <= 0:
                self.trigger_game_over()
                return

        self.snake.hue += 0.002
        # comprobar victoria por longitud objetivo (longitud puede ser mayor que len(cuerpo) momentáneamente)
        if self.snake.longitud >= (self.casillas_x * self.casillas_y):
            self.win()

    def expandir_offsets(self, new_cols, new_rows):
        # expandir filas
        for y in range(len(self.filas_offsets), new_rows + 1):
            self.filas_offsets.append([random.randint(-5,5) for _ in range(new_cols + 1)])

        # expandir columnas
        for x in range(len(self.cols_offsets), new_cols + 1):
            self.cols_offsets.append([random.randint(-5,5) for _ in range(new_rows + 1)])

        # si ya existen filas/columnas, añadir solo lo que falta
        for y in range(len(self.filas_offsets)):
            while len(self.filas_offsets[y]) < new_cols + 1:
                self.filas_offsets[y].append(random.randint(-5,5))

        for x in range(len(self.cols_offsets)):
            while len(self.cols_offsets[x]) < new_rows + 1:
                self.cols_offsets[x].append(random.randint(-5,5))


    # ----- DIBUJO -----

    def inicializar_tablero_alocado(self):
        """
        Llamar solo una vez al inicio para calcular offsets aleatorios de filas y columnas.
        Esto crea un efecto de celdas tipo rombo/geométricas.
        """
        self.filas_offsets = []
        self.cols_offsets = []

        for y in range(self.casillas_y + 1):
            # offset vertical de cada línea horizontal (altura de la fila)
            self.filas_offsets.append([random.randint(-5, 5) for _ in range(self.casillas_x + 1)])

        for x in range(self.casillas_x + 1):
            # offset horizontal de cada línea vertical (anchura de la columna)
            self.cols_offsets.append([random.randint(-5, 5) for _ in range(self.casillas_y + 1)])

    def dibujar_tablero(self):
        tam_render = self.tam
        cols = self.casillas_x
        rows = self.casillas_y

        # animación de color
        t = time.time()
        cx, cy = cols / 2, rows / 2
        max_dist = (cx**2 + cy**2)**0.5

        for y in range(rows):
            for x in range(cols):
                # Color base
                base_color = self.board_light_color if (x + y) % 2 == 0 else self.board_dark_color

                # degradado radial (más oscuro hacia los bordes)
                dist = ((x - cx)**2 + (y - cy)**2)**0.5
                radial_factor = dist / max_dist

                # animación sutil tipo “vibración de color”
                max_factor = 0.85  # no pasar del 85% del color máximo
                anim_factor = 0.10 * math.sin(t*2 + x*0.3 + y*0.3)

                color = tuple(
                    max(0, min(int(c * (1 - radial_factor*0.5 + anim_factor)), int(255*max_factor)))
                    for c in base_color
                )


                # Obtener las 4 esquinas de la celda usando offsets precomputados
                top_left = (x * tam_render + self.cols_offsets[x][y], HUD_ALTO + y * tam_render + self.filas_offsets[y][x])
                top_right = ((x+1) * tam_render + self.cols_offsets[x+1][y], HUD_ALTO + y * tam_render + self.filas_offsets[y][x+1])
                bottom_right = ((x+1) * tam_render + self.cols_offsets[x+1][y+1], HUD_ALTO + (y+1) * tam_render + self.filas_offsets[y+1][x+1])
                bottom_left = (x * tam_render + self.cols_offsets[x][y+1], HUD_ALTO + (y+1) * tam_render + self.filas_offsets[y+1][x])

                # dibujar polígono (celda irregular)
                pygame.draw.polygon(pantalla, color, [top_left, top_right, bottom_right, bottom_left])

        # --- Borde del tablero ---
        # Crear lista de puntos del perímetro usando offsets
        bordes = []

        # Lado superior
        for x in range(cols + 1):
            px = x * tam_render + self.cols_offsets[x][0]
            py = HUD_ALTO + 0 * tam_render + self.filas_offsets[0][x]
            bordes.append((px, py))

        # Lado derecho
        for y in range(1, rows + 1):
            px = (cols) * tam_render + self.cols_offsets[cols][y]
            py = HUD_ALTO + y * tam_render + self.filas_offsets[y][cols]
            bordes.append((px, py))

        # Lado inferior
        for x in reversed(range(cols)):
            px = x * tam_render + self.cols_offsets[x][rows]
            py = HUD_ALTO + rows * tam_render + self.filas_offsets[rows][x]
            bordes.append((px, py))

        # Lado izquierdo
        for y in reversed(range(1, rows)):
            px = 0 * tam_render + self.cols_offsets[0][y]
            py = HUD_ALTO + y * tam_render + self.filas_offsets[y][0]
            bordes.append((px, py))

        # # Dibujar polígono sólido de borde (color de fondo)
        # pygame.draw.polygon(pantalla, (50, 50, 50), bordes)

        # Opcional: línea roja encima para marcar perímetro
        pygame.draw.lines(pantalla, BORDE_ROJO, True, bordes, 7)



    def _get_render_positions(self, alpha: float):
        prev = list(getattr(self, 'prev_cuerpo', self.snake.cuerpo))
        cur = list(getattr(self, 'cur_cuerpo', self.snake.cuerpo))

        if not prev:
            prev = cur.copy()
        if not cur:
            cur = prev.copy()

        # Alinear longitudes (padear por delante) para interpolación
        while len(prev) < len(cur):
            prev.insert(0, prev[0])
        while len(cur) < len(prev):
            cur.insert(0, cur[0])

        render = []
        for (px, py), (cx, cy) in zip(prev, cur):
            rx = px * (1 - alpha) + cx * alpha
            ry = py * (1 - alpha) + cy * alpha
            render.append((rx, ry))
        return render
    
    # Función para dibujar una fruta aleatoria en la pantalla
    @staticmethod
    def dibujar_fruta(pantalla, rx, ry, tam_render, fruta_id):
        fruta_img = frutas[fruta_id]
        if fruta_img:
            size = int(tam_render)
            fruta_img_redim = pygame.transform.smoothscale(fruta_img, (size, size))
            pantalla.blit(fruta_img_redim, (int(rx - size/2), int(ry - size/2)))


    def dibujar_elementos(self, alpha_move=1.0):
        # calcular tam render (si estamos redimensionando interpolar)
        if getattr(self, 'resize_active', False):
            old_tam = getattr(self, 'prev_tam', self.tam)
            new_tam = self.tam
            alpha_resize = min(self.resize_timer / max(self.resize_duration, 1), 1.0)
            tam_render = old_tam * (1 - alpha_resize) + new_tam * alpha_resize
        else:
            tam_render = float(self.tam)

        # Dibujar frutas/minas interpolando si hay cambio de mapa
        if getattr(self, 'resize_active', False):
            # usar prev/cur listas si existen
            prev_f = getattr(self, 'prev_frutas', self.frutas)
            cur_f = getattr(self, 'cur_frutas', self.frutas)
            prev_m = getattr(self, 'prev_minas', self.minas)
            cur_m = getattr(self, 'cur_minas', self.minas)
            alpha_resize = min(self.resize_timer / max(self.resize_duration, 1), 1.0)

            # frutas
            for i in range(max(len(prev_f), len(cur_f))):
                p = prev_f[i] if i < len(prev_f) else prev_f[-1]
                c = cur_f[i] if i < len(cur_f) else cur_f[-1] if cur_f else p
                rx = (p[0] * (1 - alpha_resize) + c[0] * alpha_resize) * tam_render + tam_render // 2
                ry = HUD_ALTO + (p[1] * (1 - alpha_resize) + c[1] * alpha_resize) * tam_render + tam_render // 2
                fruta_id = self.frutas_ids.get(c, self.frutas_ids.get(p, 1))
                Juego.dibujar_fruta(
                    pantalla,
                    int(rx), int(ry), int(tam_render // 1.5),
                    fruta_id
                )

            # minas
            for i in range(max(len(prev_m), len(cur_m))):
                p = prev_m[i] if i < len(prev_m) else prev_m[-1]
                c = cur_m[i] if i < len(cur_m) else cur_m[-1] if cur_m else p
                rx = (p[0] * (1 - alpha_resize) + c[0] * alpha_resize) * tam_render + tam_render // 2
                ry = HUD_ALTO + (p[1] * (1 - alpha_resize) + c[1] * alpha_resize) * tam_render + tam_render // 2
                size = int(tam_render // 1.5)  # ajusta si quieres la mina más grande/pequeña
                mina_scaled = pygame.transform.smoothscale(mina_img, (size, size))
                pantalla.blit(
                    mina_scaled,
                    (int(rx - size // 2), int(ry - size // 2))
                )
        else:
            for x, y in self.frutas:
                fruta_id = self.frutas_ids.get((x, y), 1)  # <-- usar ID fijo
                Juego.dibujar_fruta(
                    pantalla,
                    x * int(tam_render) + int(tam_render)//2,
                    HUD_ALTO + y * int(tam_render) + int(tam_render)//2,
                    int(tam_render)//1.5,
                    fruta_id
                )


            for x, y in self.minas:
                rx = x * int(tam_render) + int(tam_render) // 2
                ry = HUD_ALTO + y * int(tam_render) + int(tam_render) // 2

                size = int(tam_render // 1.5)  # mismo tamaño que en resize
                mina_scaled = pygame.transform.smoothscale(mina_img, (size, size))
                pantalla.blit(
                    mina_scaled,
                    (int(rx - size // 2), int(ry - size // 2))
                )

        # --- Dibujar serpiente fluida ---
        self.draw_snake_smooth(pantalla, tam_render, HUD_ALTO, alpha_move)

        # Dibujar debug si está activado
        if getattr(self, 'ai', None) and DEBUG:
            ai = self.ai
            wm = getattr(ai, 'debug_weight_map', {})
            if wm:
                maxw = max(wm.values()) if wm.values() else 1.0
                minw = min(wm.values()) if wm.values() else 0.0
                span = max(1e-6, maxw - minw)
                small_font = pygame.font.SysFont("consolas", 12)

                for (x,y), cost in wm.items():
                    norm = (cost - minw)/span
                    alpha = int(200*(1.0-norm))
                    surf = pygame.Surface((int(tam_render), int(tam_render)), pygame.SRCALPHA)
                    surf.fill((20,200,80, alpha))
                    pantalla.blit(surf, (x*int(tam_render), HUD_ALTO + y*int(tam_render)))
                    txt = small_font.render(f"{cost:.1f}", True, (0,0,0))
                    pantalla.blit(txt, (x*int(tam_render)+2, HUD_ALTO + y*int(tam_render)+2))

            # dibujar camino
            path = getattr(ai, 'debug_path', [])
            if path and len(path) > 1:
                for i, p in enumerate(path):
                    px, py = p
                    pygame.draw.rect(pantalla, (40,100,220), (px*int(tam_render), HUD_ALTO + py*int(tam_render), int(tam_render), int(tam_render)), 2)
                    idx_txt = small_font.render(str(i), True, (40,100,220))
                    pantalla.blit(idx_txt, (px*int(tam_render)+int(tam_render)//2-idx_txt.get_width()//2,
                                            HUD_ALTO + py*int(tam_render)+int(tam_render)//2-idx_txt.get_height()//2))

    def draw_snake_smooth(self, pantalla, tam_render, HUD_ALTO, alpha_move):
        render_positions = self._get_render_positions(alpha_move)
        total = len(render_positions)
        if total < 2:
            return

        # Convertir a coordenadas de pantalla
        screen_positions = [
            (rxg * tam_render + tam_render // 2,
            HUD_ALTO + ryg * tam_render + tam_render // 2)
            for rxg, ryg in render_positions
        ]

        # Suavizar curvas usando Catmull-Rom
        smooth_points = []
        for i in range(total):
            P0 = screen_positions[max(i-1, 0)]
            P1 = screen_positions[i]
            P2 = screen_positions[min(i+1, total-1)]
            P3 = screen_positions[min(i+2, total-1)]
            smooth_points.extend(Juego.catmull_rom_spline(P0, P1, P2, P3, n_points=5))

        # Dibujar cuerpo gordito y degradado
        for i in range(len(smooth_points)-1):
            p1, p2 = smooth_points[i], smooth_points[i+1]
            t = i / max(len(smooth_points)-1, 1)
            size_factor = 0.9 + t * 0.4
            grosor = int((tam_render // 2.6) * size_factor)

            brillo = 0.4 + t * 0.6
            color = hsv_color(self.snake.hue, 1, brillo)
            pygame.draw.circle(pantalla, color, p1, max(1, grosor-2))

        # --- Ojos en la nuca ---
        # Elegimos el último punto del smooth para colocar los ojos (nuca)
        px, py = smooth_points[-1]

        # Calculamos la dirección de la cabeza para orientar los ojos
        dir_x = smooth_points[-1][0] - smooth_points[-2][0]
        dir_y = smooth_points[-1][1] - smooth_points[-2][1]
        length = max((dir_x**2 + dir_y**2) ** 0.5, 0.001)
        dir_x /= length
        dir_y /= length

        # Perpendicular para separar ojos a los lados
        perp_x, perp_y = -dir_y, dir_x
        eye_sep = grosor * 0.35   # separación lateral de los ojos
        eye_r = max(2, grosor // 3)  # radio de los ojos

        # Dibujar ambos ojos
        for side in (-1, 1):
            ex = int(px + perp_x * side * eye_sep)
            ey = int(py + perp_y * side * eye_sep)
            # ojo blanco
            pygame.draw.circle(pantalla, (240, 240, 240), (ex, ey), eye_r)
            # pupila negra
            pygame.draw.circle(
                pantalla,
                (0, 0, 0),
                (ex + int(dir_x * eye_r * 0.5), ey + int(dir_y * eye_r * 0.5)),
                eye_r // 2
            )

        
    def catmull_rom_spline(P0, P1, P2, P3, n_points=10):
        """
        Devuelve puntos interpolados entre P1 y P2 usando Catmull-Rom spline.
        P0, P1, P2, P3 son tuplas (x, y)
        n_points = número de puntos interpolados entre P1 y P2
        """
        points = []
        for i in range(n_points):
            t = i / (n_points - 1)
            t2 = t * t
            t3 = t2 * t
            x = 0.5 * ((2*P1[0]) +
                    (-P0[0] + P2[0])*t +
                    (2*P0[0] - 5*P1[0] + 4*P2[0] - P3[0])*t2 +
                    (-P0[0] + 3*P1[0] - 3*P2[0] + P3[0])*t3)
            y = 0.5 * ((2*P1[1]) +
                    (-P0[1] + P2[1])*t +
                    (2*P0[1] - 5*P1[1] + 4*P2[1] - P3[1])*t2 +
                    (-P0[1] + 3*P1[1] - 3*P2[1] + P3[1])*t3)
            points.append((x, y))
        return points

    def dibujar_hud(self):
        # Calcular ancho HUD dinámico para evitar superposición con el menú
        max_hud_w = max(ANCHO - MENU_WIDTH - 40, 120)
        hud_w = min(520, max_hud_w)
        hud_h = 44
        s = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        s.fill((10, 10, 14, 200))
        pantalla.blit(s, ((ANCHO - hud_w)//2, 6))

        # Estadísticas colocando etiquetas cortas y colores claros
        x_cursor = 18
        gap = 18
        fuente_small = pygame.font.SysFont("consolas", 18)

        def draw_stat(icon_color, label, value):
            nonlocal x_cursor
            # pequeño icono circular
            pygame.draw.circle(pantalla, icon_color, (x_cursor + 8, 14 + hud_h//2 - 2), 6)
            x_cursor += 18
            lbl = fuente_small.render(label, True, (200, 200, 200))
            pantalla.blit(lbl, (x_cursor, 14))
            x_cursor += lbl.get_width() + 6
            val = fuente_small.render(str(value), True, (255, 255, 255))
            pantalla.blit(val, (x_cursor, 14))
            x_cursor += val.get_width() + gap

        draw_stat((120,220,120), "Len", f"{self.snake.longitud}")
        draw_stat((220,180,80), "Spd", f"{self.velocidad}")
        draw_stat((200,200,200), "Map", f"{self.casillas_x}x{self.casillas_y}")
        draw_stat((180,200,255), "Time", f"{self.tiempo_vivo():.1f}s")

        # Indicador IA (ON/OFF) y riesgo
        try:
            ai_on = getattr(self, 'ai_enabled', False)
            ai_risk = getattr(self, 'ai', None).risk if getattr(self, 'ai', None) is not None else 0
            ai_color = (120, 255, 120) if ai_on else (220, 120, 120)
            pygame.draw.circle(pantalla, ai_color, (x_cursor + 8, 14 + hud_h//2 - 2), 6)
            x_cursor += 18
            txt = fuente_small.render('AI', True, (200,200,200))
            pantalla.blit(txt, (x_cursor, 14))
            x_cursor += txt.get_width() + 6
            val = fuente_small.render(f"{'ON' if ai_on else 'OFF'} r{ai_risk}", True, (255,255,255))
            pantalla.blit(val, (x_cursor, 14))
            x_cursor += val.get_width() + gap
        except Exception:
            pass

    def dibujar_menu(self):
        y0 = ALTO - MENU_HEIGHT
        pygame.draw.rect(
            pantalla,
            (25, 25, 35),
            (0, y0, ANCHO, MENU_HEIGHT)
        )

        titulo = fuente.render("ACCIONES", True, (250, 220, 130))
        pantalla.blit(titulo, (12, y0 + 8))

        acciones = {
            1: "Mapa +",
            2: "Mapa -",
            3: "Vel +",
            4: "Vel -",
            5: "Fruta",
            6: "Grow",
            7: "Mina",
            8: "Shrink",
            9: "Reset",
            0: "+10",
        }

        cols = 5
        spacing_x = ANCHO // cols
        start_y = y0 + 40

        font_btn = pygame.font.SysFont("consolas", 16)

        i = 0
        for k in [1,2,3,4,5,6,7,8,9,0]:
            col = i % cols
            row = i // cols

            x = col * spacing_x + spacing_x // 2
            y = start_y + row * 90

            # fondo botón
            pygame.draw.rect(
                pantalla,
                (45, 45, 65),
                (x - 40, y - 36, 80, 80),
                border_radius=12
            )

            icon = icons.get(k)
            if icon:
                pantalla.blit(icon, (x - ICON_SIZE//2, y - ICON_SIZE//2))
            else:
                pygame.draw.circle(pantalla, (120,120,140), (x, y), 22)

            label = font_btn.render(acciones[k], True, (220,220,220))
            pantalla.blit(label, (x - label.get_width()//2, y + 28))

            i += 1

    def win(self):
        if self.win_state:
            return
        self.win_state = True
        self.game_over = True
        self.win_time = pygame.time.get_ticks()
        # pausar tiempo jugado y empezar countdown de victoria
        if self.paused_elapsed is None:
            self.paused_elapsed = (self.win_time - self.tiempo_inicio) / 1000.0
        self.win_countdown = 10000
        # crear confeti
        self.confeti = []
        cols = [hsv_color(i/10.0) for i in range(10)]
        for _ in range(120):
            p = {
                'x': random.uniform(0, ANCHO),
                'y': random.uniform(-200, -10),
                'vx': random.uniform(-50, 50),
                'vy': random.uniform(50, 300),
                'col': random.choice(cols),
                'size': random.randint(4, 10)
            }
            self.confeti.append(p)

    def dibujar_win(self, dt):
        # fondo semi-transparente
        s = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        pantalla.blit(s, (0, 0))

        # mensaje principal centrado horizontal y 1/4 de la pantalla
        msg = fuente_grande.render("¡VICTORIA!", True, (255, 240, 60))
        pantalla.blit(msg, (ANCHO//2 - msg.get_width()//2, ALTO//4))

        # subtítulo debajo del mensaje principal
        subt = fuente.render(f"Longitud: {self.snake.longitud} / {self.casillas_x * self.casillas_y}", True, (255,255,255))
        pantalla.blit(subt, (ANCHO//2 - subt.get_width()//2, ALTO//4 + 60))

        # estadísticas resumidas más abajo
        fuente_small = pygame.font.SysFont("consolas", 20)
        stats_y = ALTO//4 + 120
        stats = [
            ("Tiempo:", f"{self.tiempo_vivo():.2f}s"),
            ("Velocidad:", f"{self.velocidad}"),
            ("Tamaño:", f"{self.casillas_x}x{self.casillas_y}"),
            ("Frutas:", f"{self.frutas_recogidas}"),
            ("Minas:", f"{self.minas_activadas}")
        ]

        for k, v in stats:
            t1 = fuente_small.render(k, True, (220, 220, 220))
            t2 = fuente_small.render(v, True, (255, 255, 200))
            pantalla.blit(t1, (20, stats_y))
            pantalla.blit(t2, (220, stats_y))
            stats_y += 28

        # animar confeti en toda la pantalla
        for c in self.confeti:
            c['x'] += c['vx'] * (dt/1000.0)
            c['y'] += c['vy'] * (dt/1000.0)
            pygame.draw.circle(pantalla, c['col'], (int(c['x']), int(c['y'])), c['size'])

        # contador grande encima del mensaje principal
        if getattr(self, 'win_countdown', None) is not None:
            remain = max(0, int(self.win_countdown / 1000))
            big = fuente_console_big.render(str(remain), True, (255, 255, 255))
            pantalla.blit(big, (ANCHO//2 - big.get_width()//2, ALTO//4 - 100))

    def dibujar_game_over(self, dt):
        # fondo semi-transparente
        s = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        s.fill((0, 0, 0, 190))
        pantalla.blit(s, (0, 0))

        # mensaje principal centrado horizontal y 1/4 de la pantalla
        msg = fuente_grande.render("GAME OVER", True, (240, 80, 80))
        pantalla.blit(msg, (ANCHO//2 - msg.get_width()//2, ALTO//4))

        # estadísticas resumidas
        fuente_small = pygame.font.SysFont("consolas", 20)
        stats_y = ALTO//4 + 80
        stats = [
            ("Tiempo:", f"{self.tiempo_vivo():.2f}s"),
            ("Velocidad:", f"{self.velocidad}"),
            ("Tamaño:", f"{self.casillas_x}x{self.casillas_y}"),
            ("Frutas:", f"{self.frutas_recogidas}"),
            ("Minas:", f"{self.minas_activadas}")
        ]

        for k, v in stats:
            t1 = fuente_small.render(k, True, (220, 220, 220))
            t2 = fuente_small.render(v, True, (255, 255, 200))
            pantalla.blit(t1, (20, stats_y))
            pantalla.blit(t2, (220, stats_y))
            stats_y += 28

        # contador grande encima del mensaje principal
        remain = max(0, int(getattr(self, 'game_over_countdown', 0) / 1000))
        cd_big = fuente_console_big.render(str(remain), True, (255, 255, 255))
        pantalla.blit(cd_big, (ANCHO//2 - cd_big.get_width()//2, ALTO//4 - 100))
 
    def dibujar_inicio(self):
        # Lista de líneas de texto a mostrar
        lineas = [
            "",
            "===================",
            "      Inserta      ",
            "      un COIN      ",
            "   para empezar    ",
            "==================="
        ]
        
        # Altura inicial
        y_inicial = ALTO // 4
        espacio = 50  # Espacio entre líneas

        for i, linea in enumerate(lineas):
            # Crear superficie de texto con fuente tipo consola
            msg = fuente_grande.render(linea, True, TEXTO_COLOR)
            # Centrar en la pantalla
            pantalla.blit(msg, (ANCHO//2 - msg.get_width()//2, y_inicial + i * espacio))



# ================= LOOP =================
juego = Juego()
juego.inicializar_tablero_alocado()  # esto prepara los offsets


# Iniciar servidor de triggers externos
run_triggers()

while True:
    # ===== TRIGGERS EXTERNOS =====
    while not trigger_queue.empty():
        key = trigger_queue.get()

        # Simular pulsación de tecla 0–9
        if key == 0:
            juego.key_counts[0] += 1
            juego.snake.crecer(10)
            juego.ai.set_difficulty(0)

        elif key == 1:
            juego.key_counts[1] += 1
            juego.ampliar_mapa()
            juego.ai.set_difficulty(1)

        elif key == 2:
            juego.key_counts[2] += 1
            juego.reducir_mapa()
            juego.ai.set_difficulty(2)

        elif key == 3:
            juego.key_counts[3] += 1
            juego.velocidad += 1
            juego.ai.set_difficulty(3)

        elif key == 4 and juego.velocidad > 1:
            juego.key_counts[4] += 1
            juego.velocidad -= 1
            juego.ai.set_difficulty(4)

        elif key == 5:
            juego.key_counts[5] += 1
            juego.frutas.append(juego.pos_libre())
            juego.ai.set_difficulty(5)

        elif key == 6:
            juego.key_counts[6] += 1
            juego.snake.crecer(1)
            juego.ai.set_difficulty(6)

        elif key == 7:
            juego.key_counts[7] += 1
            juego.minas.append(juego.pos_libre())
            juego.ai.set_difficulty(7)

        elif key == 8:
            juego.key_counts[8] += 1
            juego.snake.reducir(1)
            juego.ai.set_difficulty(8)

        elif key == 9:
            juego.key_counts[9] += 1
            juego.trigger_game_over()
            juego.ai.set_difficulty(9)

        # ===INICIAR IA CON KEY 10====
        elif key == 10 and not juego.en_juego:
            print("Iniciando partida con IA desde trigger externo")
            juego.en_juego = True
            juego.reset_partida()
            # empezar con IA
            juego.ai_enabled = True
        if not juego.en_juego:
            continue

    dt = clock.tick(FPS)
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

            if e.key == pygame.K_SPACE and not juego.en_juego:
                juego.en_juego = True
                juego.reset_partida()
                # empezar como jugador humano
                juego.ai_enabled = False

            if e.key == pygame.K_RETURN and not juego.en_juego:
                juego.en_juego = True
                juego.reset_partida()
                # empezar con IA
                juego.ai_enabled = True
            if not juego.en_juego:
                continue

            # Si hay overlay de victoria/derrota: cualquier tecla acelera el contador a 0
            if juego.win_state or juego.game_over:
                # ESC ya se maneja arriba; el resto de teclas harán que el countdown termine
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if juego.win_state:
                    juego.win_countdown = 0
                if juego.game_over:
                    juego.game_over_countdown = 0
                continue

            if e.key == pygame.K_LEFT:
                juego.snake.cambiar_direccion((-1, 0))
                juego.last_human_input = pygame.time.get_ticks()
            if e.key == pygame.K_RIGHT:
                juego.snake.cambiar_direccion((1, 0))
                juego.last_human_input = pygame.time.get_ticks()
            if e.key == pygame.K_UP:
                juego.snake.cambiar_direccion((0, -1))
                juego.last_human_input = pygame.time.get_ticks()
            if e.key == pygame.K_DOWN:
                juego.snake.cambiar_direccion((0, 1))
                juego.last_human_input = pygame.time.get_ticks()

            # Toggle IA con la tecla A
            if e.key == pygame.K_a:
                juego.ai_enabled = not getattr(juego, 'ai_enabled', False)
                print(f"AI enabled: {juego.ai_enabled}")

            if e.key == pygame.K_1:
                juego.key_counts[1] = juego.key_counts.get(1, 0) + 1
                juego.ampliar_mapa()
                juego.ai.set_difficulty(1)

            if e.key == pygame.K_2:
                juego.key_counts[2] = juego.key_counts.get(2, 0) + 1
                juego.reducir_mapa()
                juego.ai.set_difficulty(2)

            if e.key == pygame.K_3:
                juego.key_counts[3] = juego.key_counts.get(3, 0) + 1
                juego.velocidad += 1
                juego.ai.set_difficulty(3)
            if e.key == pygame.K_4 and juego.velocidad > 1:
                juego.key_counts[4] = juego.key_counts.get(4, 0) + 1
                juego.velocidad -= 1
                juego.ai.set_difficulty(4)

            if e.key == pygame.K_5:
                juego.key_counts[5] = juego.key_counts.get(5, 0) + 1
                juego.frutas.append(juego.pos_libre())
                juego.ai.set_difficulty(5)
            if e.key == pygame.K_6:
                juego.key_counts[6] = juego.key_counts.get(6, 0) + 1
                juego.snake.crecer(1)
                juego.ai.set_difficulty(6)
            if e.key == pygame.K_7:
                juego.key_counts[7] = juego.key_counts.get(7, 0) + 1
                juego.minas.append(juego.pos_libre())
                juego.ai.set_difficulty(7)
            if e.key == pygame.K_8:
                juego.key_counts[8] = juego.key_counts.get(8, 0) + 1
                juego.snake.reducir(1)
                juego.ai.set_difficulty(8)
                if juego.snake.longitud <= 0:
                    juego.trigger_game_over()
            if e.key == pygame.K_0:
                juego.key_counts[0] = juego.key_counts.get(0, 0) + 1
                juego.snake.crecer(10)
                juego.ai.set_difficulty(0)
            if e.key == pygame.K_9:
                juego.key_counts[9] = juego.key_counts.get(9, 0) + 1
                juego.trigger_game_over()
                juego.ai.set_difficulty(9)

    pantalla.fill((0, 0, 0))
    if not juego.en_juego:
        juego.dibujar_inicio()
    else:
        # Pausar la lógica de movimiento mientras haya overlay (victoria o game over)
        if not (juego.win_state or juego.game_over):
            # Actualizar acumulador de movimiento (ms)
            juego.move_acc += dt
            move_interval = int(1000 / juego.velocidad) if juego.velocidad > 0 else 1000

            # Ejecutar uno o varios pasos de movimiento si hace falta
            while juego.move_acc >= move_interval:
                juego.prev_cuerpo = list(juego.cur_cuerpo)
                # Si la IA está activada y no hubo input humano reciente, pedir decisión
                try:
                    if getattr(juego, 'ai_enabled', False):
                        now = pygame.time.get_ticks()
                        last = getattr(juego, 'last_human_input', 0)
                        if now - last > 250:
                            nd = juego.ai.get_next_move(juego)
                            if nd:
                                juego.snake.cambiar_direccion(nd)
                except Exception:
                    pass

                juego.step_move()
                juego.cur_cuerpo = list(juego.snake.cuerpo)
                juego.move_acc -= move_interval

                # comprobar recogida robusta como fallback (por si step_move no eliminó)
                try:
                    cabeza = juego.snake.cuerpo[-1]
                    if cabeza in juego.frutas:
                        while cabeza in juego.frutas:
                            juego.frutas.remove(cabeza)
                            juego.frutas_recogidas += 1
                        prev_len = juego.snake.longitud
                        juego.snake.crecer(1)
                        try:
                            juego._maybe_randomize_on_growth(prev_len)
                        except Exception:
                            pass
                        # asegurar nueva fruta
                        try:
                            juego.ensure_fruit_exists()
                        except Exception:
                            pass
                    if cabeza in juego.minas:
                        while cabeza in juego.minas:
                            juego.minas.remove(cabeza)
                            juego.minas_activadas += 1
                        juego.snake.reducir(DANO_MINA)
                        if juego.snake.longitud <= 0:
                            juego.reset_total()
                            break
                except Exception:
                    pass

                # comprobar victoria tras cada movimiento (usar longitud objetivo)
                if juego.snake.longitud >= (juego.casillas_x * juego.casillas_y):
                    juego.win()

            alpha = min(juego.move_acc / move_interval if move_interval > 0 else 1.0, 1.0)
        else:
            alpha = 1.0

        # Avanzar posible transición de resize
        if getattr(juego, 'resize_active', False):
            juego.resize_timer += dt
            if juego.resize_timer >= juego.resize_duration:
                # finalizar transición
                juego.resize_active = False
                juego.resize_timer = juego.resize_duration
                # asegurar que prev = cur
                juego.prev_cuerpo = list(juego.cur_cuerpo)
                juego.prev_frutas = list(juego.cur_frutas)
                juego.prev_minas = list(juego.cur_minas)
                juego.prev_tam = juego.tam
                # comprobar victoria al terminar resize (nuevo área) usando longitud objetivo
                if juego.snake.longitud >= (juego.casillas_x * juego.casillas_y):
                    juego.win()

        juego.dibujar_tablero()
        juego.dibujar_elementos(alpha)
        juego.dibujar_hud()
        juego.dibujar_menu()

        # Si estamos en estado de victoria usar su propio countdown y overlay
        if juego.win_state:
            if getattr(juego, 'win_countdown', None) is None:
                juego.win_countdown = 10000
            juego.win_countdown -= dt
            if juego.win_countdown <= 0:
                juego.reset_total()
                juego.en_juego = True
            else:
                juego.dibujar_win(dt)
        elif juego.game_over:
            # decrementar countdown y reiniciar cuando llegue a 0
            if getattr(juego, 'game_over_countdown', None) is None:
                juego.game_over_countdown = 10000
            juego.game_over_countdown -= dt
            if juego.game_over_countdown <= 0:
                # reiniciar partida automáticamente
                juego.reset_total()
                juego.en_juego = True
            else:
                juego.dibujar_game_over(dt)

    pygame.display.flip()
