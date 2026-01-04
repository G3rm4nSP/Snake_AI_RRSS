import pygame
import random
import os
import sys
import colorsys
# Allow importing sibling package `Player` when running this script directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from Player import PlayerAI
# TRIGGERS
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from Triggers.triggers import trigger_queue, run_triggers

pygame.init()

# ================= CONFIG =================
FPS = 60
VELOCIDAD_BASE = 8
DANO_MINA = 3

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

info = pygame.display.Info()
ANCHO = info.current_w
ALTO = info.current_h
HUD_ALTO = 50
MENU_WIDTH = 360

pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.FULLSCREEN)

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

# ================= UTIL =================
def calcular_tam_casilla(cx, cy):
    # Reservar espacio para el menú a la derecha
    available_width = max(ANCHO - MENU_WIDTH, 100)
    return min(available_width // cx, (ALTO - HUD_ALTO) // cy)

def hsv_color(h, s=1, v=1):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)

# ================= SNAKE =================
class Snake:
    def __init__(self, cx, cy):
        self.reset(cx, cy)

    def reset(self, cx, cy):
        self.direccion = (1, 0)
        self.cuerpo = [(cx // 2, cy // 2)]
        self.longitud = 5
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
        self.casillas_x = 30
        self.casillas_y = 20
        self.reset_total()

    def reset_total(self):
        self.casillas_x = 30
        self.casillas_y = 20
        self.velocidad = VELOCIDAD_BASE
        self.en_juego = False
        self.reset_partida()
        # IA y flags
        self.ai = PlayerAI()
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
        self.game_over_countdown = 10000  # ms
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
            self.frutas.append(random.choice(options))
            return

        # si no hay opciones sin minas, permitir sobreponer a mina (pero no al cuerpo)
        options2 = [p for p in all_pos if p not in forbidden]
        if options2:
            self.frutas.append(random.choice(options2))
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

    # ----- DIBUJO -----
    def dibujar_tablero(self):
        # Determinar tam y cantidad de celdas interpolado si estamos redimensionando
        if getattr(self, 'resize_active', False):
            old_tam = getattr(self, 'prev_tam', self.tam)
            new_tam = self.tam
            alpha = min(self.resize_timer / max(self.resize_duration, 1), 1.0)
            tam_render = int(old_tam * (1 - alpha) + new_tam * alpha)
            # interpolar cols/rows entre resize_from y resize_to para evitar saltos
            fx, fy = self.resize_from
            tx, ty = self.resize_to
            cols = max(1, int(round(fx * (1 - alpha) + tx * alpha)))
            rows = max(1, int(round(fy * (1 - alpha) + ty * alpha)))
        else:
            tam_render = self.tam
            cols = self.casillas_x
            rows = self.casillas_y

        for y in range(rows):
            for x in range(cols):
                color = self.board_light_color if (x + y) % 2 == 0 else self.board_dark_color
                pygame.draw.rect(
                    pantalla,
                    color,
                    (x * tam_render, HUD_ALTO + y * tam_render, tam_render, tam_render)
                )

        pygame.draw.rect(
            pantalla,
            BORDE_ROJO,
            (0, HUD_ALTO, cols * tam_render, rows * tam_render),
            4
        )

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
                pygame.draw.circle(pantalla, FRUTA_COLOR, (int(rx), int(ry)), int(tam_render // 3))

            # minas
            for i in range(max(len(prev_m), len(cur_m))):
                p = prev_m[i] if i < len(prev_m) else prev_m[-1]
                c = cur_m[i] if i < len(cur_m) else cur_m[-1] if cur_m else p
                rx = (p[0] * (1 - alpha_resize) + c[0] * alpha_resize) * tam_render + tam_render // 2
                ry = HUD_ALTO + (p[1] * (1 - alpha_resize) + c[1] * alpha_resize) * tam_render + tam_render // 2
                pygame.draw.circle(pantalla, MINA_COLOR, (int(rx), int(ry)), int(tam_render // 3))
        else:
            for x, y in self.frutas:
                pygame.draw.circle(
                    pantalla,
                    FRUTA_COLOR,
                    (x * int(tam_render) + int(tam_render) // 2,
                     HUD_ALTO + y * int(tam_render) + int(tam_render) // 2),
                    int(tam_render) // 3
                )

            for x, y in self.minas:
                pygame.draw.circle(
                    pantalla,
                    MINA_COLOR,
                    (x * int(tam_render) + int(tam_render) // 2,
                     HUD_ALTO + y * int(tam_render) + int(tam_render) // 2),
                    int(tam_render) // 3
                )

        # Dibujar serpiente usando posiciones interpoladas por movimiento, y con tam render interpolado
        render_positions = self._get_render_positions(alpha_move)
        total = len(render_positions)
        for i, (rxg, ryg) in enumerate(render_positions):
            brillo = 1 - (i / max(total, 1)) * 0.6
            color = hsv_color(self.snake.hue, 1, brillo)
            px = int(rxg * tam_render + tam_render // 2)
            py = int(HUD_ALTO + ryg * tam_render + tam_render // 2)
            pygame.draw.circle(
                pantalla,
                color,
                (px, py),
                int(tam_render // 2) - 2
            )

    def dibujar_hud(self):
        # Calcular ancho HUD dinámico para evitar superposición con el menú
        max_hud_w = max(ANCHO - MENU_WIDTH - 40, 120)
        hud_w = min(520, max_hud_w)
        hud_h = 44
        s = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
        s.fill((10, 10, 14, 200))
        pantalla.blit(s, (10, 6))

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
        # panel derecho
        x0 = ANCHO - MENU_WIDTH
        pygame.draw.rect(pantalla, (30, 30, 40), (x0, HUD_ALTO, MENU_WIDTH, ALTO - HUD_ALTO))
        # título
        titulo = fuente_grande.render("MENU", True, (250, 220, 130))
        pantalla.blit(titulo, (x0 + 12, HUD_ALTO + 8))

        # descripciones por botón
        acciones = {
            1: "Aumenta mapa",
            2: "Disminuye mapa",
            3: "Aumenta velocidad",
            4: "Disminuye velocidad",
            5: "Añade fruta",
            6: "Crecimiento +1",
            7: "Añade mina",
            8: "Reduce serpiente",
            9: "Reseteo total",
            0: "Crece +100 de longitud",
        }

        y = HUD_ALTO + 70
        pad = 12
        row_margin = 12
        row_spacing = 10
        menu_font = pygame.font.SysFont("consolas", 14)
        # etiquetas acortadas para asegurar que entren
        acciones_short = {
            1: "Aumentar mapa",
            2: "Reducir mapa",
            3: "Aumentar velocidad",
            4: "Disminuir velocidad",
            5: "Añadir fruta",
            6: "Aumentar longitud",
            7: "Añadir mina",
            8: "Reducir longitud",
            9: "Reseteo total",
            0: "Crece +100 de longitud",
        }

        # mostrar botones en orden 1..9 y luego 0 debajo del 9
        for i in [1,2,3,4,5,6,7,8,9,0]:
            # fondo de fila con margin horizontal
            bg_x = x0 + 10 + row_margin
            bg_y = y - 6
            bg_w = max(40, MENU_WIDTH - 20 - row_margin * 2)
            pygame.draw.rect(pantalla, (40, 40, 55), (bg_x, bg_y, bg_w, ICON_SIZE + pad), border_radius=8)

            # icono (desplazado respecto al bg)
            icon_x = bg_x + 8
            icon = icons.get(i)
            if icon:
                pantalla.blit(icon, (icon_x, y))
            else:
                pygame.draw.rect(pantalla, (120, 120, 140), (icon_x, y, ICON_SIZE, ICON_SIZE))

            # texto (más descriptivo)
            label = acciones_short.get(i, acciones.get(i, ''))
            txt_surface = menu_font.render(f"{i}. {label}", True, (220, 220, 220))
            pantalla.blit(txt_surface, (icon_x + ICON_SIZE + 16, y + ICON_SIZE//4))

            y += ICON_SIZE + pad + row_spacing

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

        msg = fuente_grande.render("¡VICTORIA!", True, (255, 240, 60))
        pantalla.blit(msg, (ANCHO//2 - msg.get_width()//2, ALTO//2 - 80))

        subt = fuente.render(f"Longitud: {self.snake.longitud} / {self.casillas_x * self.casillas_y}", True, (255,255,255))
        pantalla.blit(subt, (ANCHO//2 - subt.get_width()//2, ALTO//2 - 20))

        # estadísticas detalladas
        fuente_small = pygame.font.SysFont("consolas", 20)
        left = ANCHO//2 - msg.get_width()//2
        top = ALTO//2 + 20

        # tiempo a la victoria
        if self.win_time is None:
            tiempo_win = 0.0
        else:
            tiempo_win = (self.win_time - self.tiempo_inicio) / 1000.0

        avg_speed = 0.0
        if len(self.speed_samples) > 0:
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)

        stats = [
            ("Tiempo:", f"{tiempo_win:.2f}s"),
            ("Velocidad media:", f"{avg_speed:.2f}"),
            ("Vel final:", f"{self.velocidad}"),
            ("Longitud final:", f"{self.snake.longitud}"),
            ("Tamaño final:", f"{self.casillas_x}x{self.casillas_y}")
        ]

        iy = top
        for k, v in stats:
            t1 = fuente_small.render(k, True, (220, 220, 220))
            t2 = fuente_small.render(v, True, (255, 255, 200))
            pantalla.blit(t1, (left, iy))
            pantalla.blit(t2, (left + 220, iy))
            iy += 26

        # conteo de teclas 1..9
        iy += 8
        t_title = fuente_small.render("Teclas (1-9):", True, (200,200,255))
        pantalla.blit(t_title, (left, iy))
        iy += 26
        # mostrar en filas de 3
        colx = [left, left + 140, left + 280]
        for i in range(1, 10):
            cnt = self.key_counts.get(i, 0)
            txt = fuente_small.render(f"{i}: x{cnt}", True, (230,230,230))
            cx = colx[(i-1) % 3]
            cy = iy + ((i-1)//3) * 24
            pantalla.blit(txt, (cx, cy))
        # frutas/minas recogidas
        iy += 90
        t_fm = fuente_small.render("Recolectadas:", True, (200,200,255))
        pantalla.blit(t_fm, (left, iy))
        iy += 28
        t_fr = fuente_small.render(f"Frutas: x{self.frutas_recogidas}", True, (140,255,140))
        pantalla.blit(t_fr, (left, iy))
        iy += 24
        t_mi = fuente_small.render(f"Minas: x{self.minas_activadas}", True, (255,140,140))
        pantalla.blit(t_mi, (left, iy))

        # animar confeti
        for c in self.confeti:
            c['x'] += c['vx'] * (dt/1000.0)
            c['y'] += c['vy'] * (dt/1000.0)
            pygame.draw.circle(pantalla, c['col'], (int(c['x']), int(c['y'])), c['size'])
        # contador grande encima del mensaje (si existe win_countdown)
        if getattr(self, 'win_countdown', None) is not None:
            remain = max(0, int(self.win_countdown / 1000))
            big = fuente_console_big.render(str(remain), True, (255, 255, 255))
            pantalla.blit(big, (ANCHO//2 - big.get_width()//2, ALTO//2 - 220))

    def dibujar_game_over(self, dt):
        # Similar a dibujar_win pero sin confeti y con cuenta atrás de 10s
        s = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        s.fill((0, 0, 0, 190))
        pantalla.blit(s, (0, 0))

        msg = fuente_grande.render("GAME OVER", True, (240, 80, 80))
        pantalla.blit(msg, (ANCHO//2 - msg.get_width()//2, ALTO//2 - 120))

        fuente_small = pygame.font.SysFont("consolas", 20)
        left = ANCHO//2 - 220
        top = ALTO//2 - 40

        # tiempo desde inicio hasta game over
        if getattr(self, 'game_over_time', None) is None:
            tiempo_go = 0.0
        else:
            tiempo_go = (self.game_over_time - self.tiempo_inicio) / 1000.0

        avg_speed = 0.0
        if len(self.speed_samples) > 0:
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)

        stats = [
            ("Tiempo:", f"{tiempo_go:.2f}s"),
            ("Velocidad media:", f"{avg_speed:.2f}"),
            ("Vel final:", f"{self.velocidad}"),
            ("Longitud final:", f"{self.snake.longitud}"),
            ("Tamaño final:", f"{self.casillas_x}x{self.casillas_y}")
        ]

        iy = top
        for k, v in stats:
            t1 = fuente_small.render(k, True, (220, 220, 220))
            t2 = fuente_small.render(v, True, (255, 255, 200))
            pantalla.blit(t1, (left, iy))
            pantalla.blit(t2, (left + 200, iy))
            iy += 26

        # tecla counts
        iy += 8
        t_title = fuente_small.render("Teclas (1-9):", True, (200,200,255))
        pantalla.blit(t_title, (left, iy))
        iy += 26
        colx = [left, left + 140, left + 280]
        for i in range(1, 10):
            cnt = self.key_counts.get(i, 0)
            txt = fuente_small.render(f"{i}: x{cnt}", True, (230,230,230))
            cx = colx[(i-1) % 3]
            cy = iy + ((i-1)//3) * 24
            pantalla.blit(txt, (cx, cy))

        # frutas/minas recogidas
        iy += 90
        t_fm = fuente_small.render("Recolectadas:", True, (200,200,255))
        pantalla.blit(t_fm, (left, iy))
        iy += 28
        t_fr = fuente_small.render(f"Frutas: x{self.frutas_recogidas}", True, (140,255,140))
        pantalla.blit(t_fr, (left, iy))
        iy += 24
        t_mi = fuente_small.render(f"Minas: x{self.minas_activadas}", True, (255,140,140))
        pantalla.blit(t_mi, (left, iy))

        # countdown visual
        if getattr(self, 'game_over_countdown', None) is None:
            remain = 0
        else:
            remain = max(0, int(self.game_over_countdown / 1000))
        # mostrar countdown grande encima del mensaje
        cd_big = fuente_console_big.render(str(remain), True, (255, 255, 255))
        pantalla.blit(cd_big, (ANCHO//2 - cd_big.get_width()//2, ALTO//2 - 220))
        
    def dibujar_inicio(self):
        msg = fuente_grande.render("Pulsa ESPACIO para iniciar", True, TEXTO_COLOR)
        pantalla.blit(msg, (ANCHO//2 - msg.get_width()//2,
                            ALTO//2 - msg.get_height()//2))

# ================= LOOP =================
juego = Juego()

# Iniciar servidor de triggers externos
run_triggers()

while True:
    # ===== TRIGGERS EXTERNOS =====
    while not trigger_queue.empty():
        key = trigger_queue.get()

        # Simular pulsación de tecla 0–9
        if key == 0:
            juego.key_counts[0] += 1
            juego.snake.crecer(100)
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
                juego.snake.crecer(100)
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
