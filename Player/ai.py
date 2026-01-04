import heapq
import time
from collections import deque


class PlayerAI:
    """AI simple que busca fruta con A* y evita colisiones inmediatas.
    Parámetros básicos:
    - risk: 0..9, mayor valor = más agresivo (prefiere comer incluso cerca minas)
    """
    def __init__(self):
        self.risk = 5
        # historial circular de decisiones recientes (clave, move)
        self.recent = deque(maxlen=200)

    def set_difficulty(self, v: int):
        try:
            self.risk = max(0, min(9, int(v)))
        except Exception:
            pass

    def get_next_move(self, juego):
        """Devuelve una dirección (dx,dy) para el siguiente movimiento.
        Recibe el objeto `juego` que contiene el estado actual.
        """
        # Estado
        head = juego.snake.cuerpo[-1]
        cols, rows = juego.casillas_x, juego.casillas_y
        fruits = list(juego.frutas)
        mines = set(juego.minas)
        body_list = list(juego.snake.cuerpo)  # ordenado: cola ... cabeza
        body = set(body_list)
        desired_length = getattr(juego.snake, 'longitud', len(body_list))

        # Vecinos posibles
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        def in_bounds(p):
            x, y = p
            return 0 <= x < cols and 0 <= y < rows

        def is_block(p):
            # considerar cuerpo y minas como bloqueos
            return (p in body) or (p in mines)

        # Si no hay frutas, intentar moverse evitando muerte inmediata
        if not fruits:
            for dx, dy in neighbors:
                np = (head[0] + dx, head[1] + dy)
                if in_bounds(np) and not is_block(np):
                    move = (dx, dy)
                    # registrar contexto
                    try:
                        key = self._make_key(juego, move)
                        self.recent.append((key, move))
                    except Exception:
                        pass
                    return move
            # fallback mantener dirección actual
            return juego.snake.direccion

        # Buscar fruta más cercana (por Manhattan)
        fruits_sorted = sorted(fruits, key=lambda f: abs(f[0]-head[0]) + abs(f[1]-head[1]))
        target = fruits_sorted[0]

        # A* desde head hasta target
        def heuristic(a, b):
            return abs(a[0]-b[0]) + abs(a[1]-b[1])

        start = head
        frontier = []
        heapq.heappush(frontier, (0 + heuristic(start, target), 0, start, None))
        came_from = {start: None}
        cost_so_far = {start: 0}

        max_nodes = cols * rows * 2
        nodes = 0
        found = False
        end_node = None

        while frontier and nodes < max_nodes:
            _, cost, current, _ = heapq.heappop(frontier)
            nodes += 1
            if current == target:
                found = True
                end_node = current
                break

            for dx, dy in neighbors:
                nxt = (current[0] + dx, current[1] + dy)
                if not in_bounds(nxt):
                    continue
                # costo base
                extra = 0
                if nxt in mines:
                    extra += 100 - (self.risk * 8)  # menos penalización si riesgo alto
                # penalizar pasos sobre el cuerpo (excepto la cola, que puede moverse)
                tail = body_list[0] if body_list else None
                if nxt in body and nxt != tail:
                    continue

                # penalizar cercanía a minas
                for ddx, ddy in neighbors:
                    adj = (nxt[0] + ddx, nxt[1] + ddy)
                    if adj in mines:
                        extra += 6

                new_cost = cost_so_far[current] + 1 + extra
                if nxt not in cost_so_far or new_cost < cost_so_far[nxt]:
                    cost_so_far[nxt] = new_cost
                    priority = new_cost + heuristic(nxt, target)
                    heapq.heappush(frontier, (priority, new_cost, nxt, current))
                    came_from[nxt] = current

        if not found:
            # fallback: moverse hacia cualquier casilla segura (BFS hasta encontrar uno)
            for dx, dy in neighbors:
                np_ = (head[0] + dx, head[1] + dy)
                if in_bounds(np_) and np_ not in body and np_ not in mines:
                    move = (dx, dy)
                    try:
                        key = self._make_key(juego, move)
                        self.recent.append((key, move))
                    except Exception:
                        pass
                    return move
            return juego.snake.direccion

        # reconstruir camino
        path = []
        cur = end_node
        while cur and cur != start:
            path.append(cur)
            cur = came_from.get(cur)
        path.reverse()
        if not path:
            return juego.snake.direccion
        first = path[0]
        dx = first[0] - head[0]
        dy = first[1] - head[1]

        # Evaluar riesgo de quedar encerrado: BFS de área alcanzable
        def reachable_area(start_cell, body_set_fixed, mines_set):
            from collections import deque
            q = deque()
            q.append(start_cell)
            seen = {start_cell}
            mine_count = 0
            max_visits = cols * rows
            while q and len(seen) < max_visits:
                cx, cy = q.popleft()
                for ddx, ddy in neighbors:
                    nx, ny = cx + ddx, cy + ddy
                    p = (nx, ny)
                    if not in_bounds(p) or p in seen or p in body_set_fixed:
                        continue
                    seen.add(p)
                    if p in mines_set:
                        mine_count += 1
                    q.append(p)
            return len(seen), mine_count

        # Simular toda la ruta y comprobar colisiones/espacio libre en cada paso.
        sim = list(body_list)  # cola..cabeza
        safe = True
        # Hacer la IA más agresiva: reducir penalización por minas y favorecer distancia
        mine_penalty = max(0.2, (10 - self.risk) * 0.6)
        # usar set para frutas dinámicos
        fruits_set = set(fruits)
        sim_desired = desired_length
        DAMAGE_MINE = 3
        # margen de seguridad: evitar entrar en áreas demasiado pequeñas (callejones)
        safety_margin = max(4, len(body_list) // 2 + 2)
        for step_pos in path:        
            sim.append(step_pos)
            # si comemos fruta en el paso, aumentar longitud objetivo
            if step_pos in fruits_set:
                fruits_set.remove(step_pos)
                sim_desired += 1
            # si activamos mina en el paso, reducir longitud objetivo
            if step_pos in mines:
                sim_desired -= DAMAGE_MINE
            # mover cola mientras el cuerpo sea mayor que la longitud deseada tras efectos
            while len(sim) > sim_desired:
                sim.pop(0)
            # si la longitud deseada cae a 0 o menos -> muerte simulada
            if sim_desired <= 0:
                safe = False
                break
            # colisión con sí mismo?
            if len(sim) != len(set(sim)):
                safe = False
                break
            # comprobar área alcanzable desde la cabeza simulada
            area, mines_near = reachable_area(step_pos, set(sim), mines)
            # si el area disponible es menor que la longitud que tendremos + margen, es inseguro
            if area < sim_desired + safety_margin:
                safe = False
                break
            # Adicional: comprobar que existe una ruta desde la cabeza simulada hasta la cola
            # (si puede alcanzar la cola, suele existir una salida). Implementar BFS que permita
            # llegar a la cola aunque ésta esté en el conjunto (porque la cola se moverá).
            from collections import deque as _deque
            def path_exists(src, dst, blocked_set):
                q2 = _deque()
                q2.append(src)
                seen2 = {src}
                maxv = cols * rows
                while q2 and len(seen2) < maxv:
                    cx2, cy2 = q2.popleft()
                    if (cx2, cy2) == dst:
                        return True
                    for ddx, ddy in neighbors:
                        nx2, ny2 = cx2 + ddx, cy2 + ddy
                        p2 = (nx2, ny2)
                        if not in_bounds(p2) or p2 in seen2:
                            continue
                        # permitimos entrar en dst aunque esté en blocked_set
                        if p2 in blocked_set and p2 != dst:
                            continue
                        seen2.add(p2)
                        q2.append(p2)
                return False

            sim_tail = sim[0]
            if not path_exists(step_pos, sim_tail, set(sim)):
                # no puede alcanzar su cola -> riesgo de encierro
                safe = False
                break

        if safe:
            chosen = (dx, dy)
            try:
                key = self._make_key(juego, chosen)
                self.recent.append((key, chosen))
            except Exception:
                pass
            return chosen

        # Si el camino fue inseguro, usar beam-search/rollout para evaluar consecuencias (depth-limited)
        # Búsqueda más amplia/profunda: aumenta profundidad/ancho del beam
        beam_depth = 10
        beam_width = 6
        tail = body_list[0] if body_list else None

        def simulate_rollout(sim_body, sim_len, fruits_s, mines_s, target_pos, steps):
            """Simula `steps` movimientos con heurística greedy y devuelve una puntuación.
            Devuelve (score, alive, fruits_eaten, final_head, final_body_set)
            """
            sb = list(sim_body)
            s_len = sim_len
            fruits_local = set(fruits_s)
            head_pos = sb[-1]
            fruits_eaten = 0
            alive = True
            for _ in range(steps):
                # generar acciones válidas
                best_move = None
                best_score = float('-inf')
                for mdx, mdy in neighbors:
                    np_ = (head_pos[0] + mdx, head_pos[1] + mdy)
                    if not in_bounds(np_):
                        continue
                    if np_ in sb and np_ != sb[0]:
                        continue
                    # simular un paso
                    tmp = list(sb)
                    tmp.append(np_)
                    tmp_len = s_len
                    eat = 0
                    if np_ in fruits_local:
                        fruits_local.remove(np_)
                        tmp_len += 1
                        eat = 1
                    if np_ in mines_s:
                        tmp_len -= DAMAGE_MINE
                    while len(tmp) > tmp_len:
                        tmp.pop(0)
                    if tmp_len <= 0 or len(tmp) != len(set(tmp)):
                        continue
                    area_tmp, mines_tmp = reachable_area(np_, set(tmp), mines_s)
                    # evitar movimientos que lleven a áreas demasiado pequeñas
                    if area_tmp < tmp_len + safety_margin:
                        continue
                    # score local: area - mines*penalty - dist + fruit bonus
                    sc = area_tmp - mines_tmp * mine_penalty - 1.2 * heuristic(np_, target_pos) + eat * 60
                    if sc > best_score:
                        best_score = sc
                        best_move = (mdx, mdy, np_, tmp, tmp_len, eat)
                if best_move is None:
                    alive = False
                    break
                # aplicar mejor movimiento
                mdx, mdy, new_head, new_body, new_len, ate = best_move
                sb = new_body
                s_len = new_len
                head_pos = new_head
                fruits_eaten += ate
            if not alive:
                return (float('-inf'), False, fruits_eaten, head_pos, set(sb))
            final_area, final_mines = reachable_area(head_pos, set(sb), mines_s)
            score = final_area - final_mines * mine_penalty - 1.2 * heuristic(head_pos, target_pos) + fruits_eaten * 80
            return (score, True, fruits_eaten, head_pos, set(sb))

        candidates = []
        for ndx, ndy in neighbors:
            candidate = (head[0] + ndx, head[1] + ndy)
            if not in_bounds(candidate):
                continue
            if candidate in body and candidate != tail:
                continue
            # simular primer paso
            sim2 = list(body_list)
            sim2.append(candidate)
            sim2_len = desired_length
            eat0 = 0
            if candidate in fruits_set:
                fruits0 = set(fruits_set)
                fruits0.remove(candidate)
                sim2_len += 1
                eat0 = 1
            else:
                fruits0 = set(fruits_set)
            if candidate in mines:
                sim2_len -= DAMAGE_MINE
            while len(sim2) > sim2_len:
                sim2.pop(0)
            if sim2_len <= 0 or len(sim2) != len(set(sim2)):
                continue
            # fast eval
            area2, m2 = reachable_area(candidate, set(sim2), mines)
            # descartar si la zona accesible es demasiado pequeña (salvo si es la fruta objetivo)
            if area2 < sim2_len + safety_margin and candidate != target:
                continue
            fast_score = area2 - m2 * mine_penalty - 1.2 * heuristic(candidate, target) + eat0 * 60
            candidates.append((fast_score, ndx, ndy, sim2, sim2_len, fruits0))

        if not candidates:
            # sin candidatos válidos -> usar Hamiltoniano
            hmove = self.get_hamiltonian_move(juego)
            try:
                key = self._make_key(juego, hmove)
                self.recent.append((key, hmove))
            except Exception:
                pass
            return hmove

        # ordenar y hacer rollouts para top beam_width
        candidates.sort(reverse=True, key=lambda x: x[0])
        best_overall = (float('-inf'), None)
        for i, (fs, ndx, ndy, sim_init, sim_len_init, fruits_init) in enumerate(candidates[:beam_width]):
            # profundidad restante
            rem = max(0, beam_depth - 1)
            sc, alive, fe, fh, fbset = simulate_rollout(sim_init, sim_len_init, fruits_init, mines, target, rem)
            total_score = sc
            if total_score > best_overall[0]:
                best_overall = (total_score, (ndx, ndy))

        # si la mejor opción tiene score negativo o muy baja, usar hamiltoniano
        if best_overall[1] is None or best_overall[0] < 0:
            hmove = self.get_hamiltonian_move(juego)
            try:
                key = self._make_key(juego, hmove)
                self.recent.append((key, hmove))
            except Exception:
                pass
            return hmove

        chosen = best_overall[1]
        try:
            key = self._make_key(juego, chosen)
            self.recent.append((key, chosen))
        except Exception:
            pass
        return chosen

    # ---------------- Learning / Memory ----------------
    def _make_key(self, juego, move):
        # crear una firma compacta del entorno local y la acción
        head = juego.snake.cuerpo[-1]
        cols, rows = juego.casillas_x, juego.casillas_y
        radius = 6
        bx = []
        for x in range(head[0]-radius, head[0]+radius+1):
            for y in range(head[1]-radius, head[1]+radius+1):
                if x < 0 or y < 0 or x >= cols or y >= rows:
                    bx.append('W')
                    continue
                p = (x, y)
                if p in juego.snake.cuerpo:
                    bx.append('B')
                elif p in juego.minas:
                    bx.append('M')
                elif p in juego.frutas:
                    bx.append('F')
                else:
                    bx.append('.')
        # añadir move y longitud y risk
        key = f"{''.join(bx)}|{move[0]},{move[1]}|L{juego.snake.longitud}|R{self.risk}"
        return key
    # Nota: el aprendizaje persistente fue eliminado — sólo usamos heurísticas y simulación.

    # ---------------- Hamiltonian fallback ----------------
    def build_hamiltonian_cycle(self, cols, rows):
        """Construye un ciclo tipo serpiente que cubre todas las celdas.
        Si una dimensión es par, se obtiene un ciclo válido; en otros casos
        devolvemos un recorrido serpentina que se usará como fallback.
        """
        cycle = []
        # usar serpentina por filas
        for y in range(rows):
            if y % 2 == 0:
                for x in range(cols):
                    cycle.append((x, y))
            else:
                for x in range(cols - 1, -1, -1):
                    cycle.append((x, y))
        return cycle

    def get_hamiltonian_move(self, juego):
        cols, rows = juego.casillas_x, juego.casillas_y
        cycle = self.build_hamiltonian_cycle(cols, rows)
        n = len(cycle)
        head = juego.snake.cuerpo[-1]
        body = set(juego.snake.cuerpo)
        tail = juego.snake.cuerpo[0] if juego.snake.cuerpo else None
        # índice del head en el ciclo
        try:
            idx = cycle.index(head)
        except ValueError:
            # si head no está (imposible), fallback a movimiento seguro
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                np_ = (head[0]+dx, head[1]+dy)
                if 0 <= np_[0] < cols and 0 <= np_[1] < rows and np_ not in body:
                    return (dx, dy)
            return juego.snake.direccion

        # objetivo siguiente en el ciclo
        next_idx = (idx + 1) % n
        target = cycle[next_idx]
        # si el siguiente está libre o es la cola, seguirlo
        if target not in body or target == tail:
            return (target[0] - head[0], target[1] - head[1])

        # buscar vecino que avanza en el ciclo (mínima distancia adelante)
        best = None
        best_forward = n
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            cand = (head[0]+dx, head[1]+dy)
            if not (0 <= cand[0] < cols and 0 <= cand[1] < rows):
                continue
            if cand in body and cand != tail:
                continue
            try:
                cand_idx = cycle.index(cand)
            except ValueError:
                continue
            # forward distance modulo n
            forward = (cand_idx - idx) % n
            if forward == 0:
                forward = n
            if forward < best_forward:
                best_forward = forward
                best = (dx, dy)

        if best is not None:
            return best

        # como último recurso, mover a cualquier vecino seguro
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            np_ = (head[0]+dx, head[1]+dy)
            if 0 <= np_[0] < cols and 0 <= np_[1] < rows and np_ not in body:
                return (dx, dy)
        return juego.snake.direccion
