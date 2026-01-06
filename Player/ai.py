import heapq
from collections import deque

class PlayerAI:
    def __init__(self):
        self.risk = 5
        self.memory = deque(maxlen=100)  # memoriza posiciones recientes de la serpiente
        self.body_length_memory = 0

    def set_difficulty(self, v: int):
        self.risk = max(0, min(9, int(v)))

    # ==========================================================
    # MAIN ENTRY
    # ==========================================================
    def get_next_move(self, juego):
        head = juego.snake.cuerpo[-1]
        body = list(juego.snake.cuerpo)
        tail = body[0] if body else head
        body_set = set(body)
        fruits = set(juego.frutas)
        mines = set(juego.minas)
        cols, rows = juego.casillas_x, juego.casillas_y
        neighbors = [(-1,0),(1,0),(0,-1),(0,1)]

        # ---------- Actualizar memoria ----------
        if self.body_length_memory != len(body):
            self.memory = deque(list(body), maxlen=len(body))
            self.body_length_memory = len(body)
        else:
            self.memory.append(body[-1])

        # ---------- Detectar bucle ----------
        in_loop = list(self.memory) == body

        # ---------- 1️⃣ Ir hacia frutas ----------
        if fruits:
            move = self.move_to_fruit(head, body, tail, fruits, mines, cols, rows, neighbors)
            if move:
                return move

        # ---------- 2️⃣ Reorganización anti-bucle ----------
        if in_loop:
            move = self.reorganization_move(head, body, mines, cols, rows)
            if move and self.is_safe_move(head, move, body, mines, cols, rows):
                return move

        # ---------- 3️⃣ Seguir la cola ----------
        path_to_tail = self.a_star(head, tail, body_set, tail, mines, cols, rows)
        if path_to_tail:
            step = path_to_tail[0]
            return (step[0]-head[0], step[1]-head[1])

        # ---------- 4️⃣ Fallback Hamiltoniano ----------
        return self.get_hamiltonian_move(juego)

    # ==========================================================
    # MOVIMIENTO HACIA FRUTAS
    # ==========================================================
    def move_to_fruit(self, head, body, tail, fruits, mines, cols, rows, neighbors):
        body_set = set(body)
        reachable_fruits = sorted(fruits, key=lambda f: abs(f[0]-head[0])+abs(f[1]-head[1]))
        for target in reachable_fruits:
            path = self.a_star(head, target, body_set, tail, mines, cols, rows, avoid_ring=True)
            if path:
                first = path[0]
                move = (first[0]-head[0], first[1]-head[1])

                # Evitar mina si hay alternativa
                if first in mines:
                    for dx, dy in neighbors:
                        alt = (head[0]+dx, head[1]+dy)
                        if alt not in mines and self.is_safe_move(head, (dx, dy), body, mines, cols, rows):
                            move = (dx, dy)
                            break

                if self.is_safe_move(head, move, body, mines, cols, rows):
                    return move
        return None

    # ==========================================================
    # A* PATHFINDING (evita anillo externo opcionalmente)
    # ==========================================================
    def a_star(self, start, goal, body, tail, mines, cols, rows, avoid_ring=False):
        def h(a,b): return abs(a[0]-b[0]) + abs(a[1]-b[1])

        neighbors = [(-1,0),(1,0),(0,-1),(0,1)]
        frontier = [(0, start)]
        came_from = {start: None}
        cost = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)
            if current == goal:
                break
            for dx, dy in neighbors:
                nxt = (current[0]+dx, current[1]+dy)
                if not (0 <= nxt[0] < cols and 0 <= nxt[1] < rows): continue
                if nxt in body and nxt != tail: continue
                if avoid_ring and (nxt[0]==0 or nxt[0]==cols-1 or nxt[1]==0 or nxt[1]==rows-1) and nxt != goal:
                    continue

                extra = 20 if nxt in mines else 0
                new_cost = cost[current] + 1 + extra
                if nxt not in cost or new_cost < cost[nxt]:
                    cost[nxt] = new_cost
                    heapq.heappush(frontier, (new_cost + h(nxt, goal), nxt))
                    came_from[nxt] = current

        if goal not in came_from: return None

        path, cur = [], goal
        while cur != start:
            path.append(cur)
            cur = came_from[cur]
        path.reverse()
        return path

    # ==========================================================
    # SAFETY CHECK
    # ==========================================================
    def is_safe_move(self, head, move, body, mines, cols, rows):
        nx, ny = head[0]+move[0], head[1]+move[1]
        new_head = (nx, ny)
        if not(0 <= nx < cols and 0 <= ny < rows): return False
        if new_head in body[:-1] or new_head in mines: return False

        sim = body[1:] + [new_head]
        sim_set = set(sim)

        # Área alcanzable
        q, seen = deque([new_head]), {new_head}
        while q:
            x, y = q.popleft()
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                p = (x+dx, y+dy)
                if 0<=p[0]<cols and 0<=p[1]<rows and p not in seen and p not in sim_set and p not in mines:
                    seen.add(p)
                    q.append(p)
        if len(seen) < len(sim)+2: return False

        # Puede alcanzar la cola
        if not self.path_exists(new_head, sim[0], sim_set, mines, cols, rows): return False
        return True

    def path_exists(self, start, goal, blocked, mines, cols, rows):
        q, seen = deque([start]), {start}
        while q:
            x, y = q.popleft()
            if (x, y) == goal: return True
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                p = (x+dx, y+dy)
                if 0<=p[0]<cols and 0<=p[1]<rows and p not in seen and (p not in blocked or p == goal) and p not in mines:
                    seen.add(p)
                    q.append(p)
        return False

    # ==========================================================
    # REORGANIZACIÓN ANTI-BUCLE MEJORADA
    # ==========================================================
    def reorganization_move(self, head, body, mines, cols, rows):
        neighbors = [(-1,0),(1,0),(0,-1),(0,1)]
        body_set = set(body)

        # 1️⃣ Hueco interior más grande
        best, best_free = None, -1
        for dx, dy in neighbors:
            nx, ny = head[0]+dx, head[1]+dy
            if 1<=nx<cols-1 and 1<=ny<rows-1 and (nx,ny) not in body_set and (nx,ny) not in mines:
                free = self.count_reachable((nx,ny), body_set, mines, cols, rows, avoid_ring=True)
                if free > best_free:
                    best_free = free
                    best = (dx, dy)
        if best: return best

        # 2️⃣ Buscar cualquier movimiento seguro que permita zigzag
        safe_moves = []
        for dx, dy in neighbors:
            nx, ny = head[0]+dx, head[1]+dy
            new_head = (nx, ny)
            if 0<=nx<cols and 0<=ny<rows and new_head not in body_set and new_head not in mines:
                # Comprobar que no queda atrapado
                sim = body[1:] + [new_head]
                sim_set = set(sim)
                reachable = self.count_reachable(new_head, sim_set, mines, cols, rows)
                if reachable >= 3:  # al menos espacio para moverse y volver
                    safe_moves.append((dx, dy))

        if safe_moves:
            # Priorizar movimiento con más espacio alrededor
            best_move = max(safe_moves, key=lambda m: self.count_reachable((head[0]+m[0], head[1]+m[1]), body_set, mines, cols, rows))
            return best_move

        # 3️⃣ fallback: cualquier vecino seguro
        for dx, dy in neighbors:
            nx, ny = head[0]+dx, head[1]+dy
            if 0<=nx<cols and 0<=ny<rows and (nx,ny) not in body_set and (nx,ny) not in mines:
                return (dx, dy)

        return None

    def count_reachable(self, start, body_set, mines, cols, rows, avoid_ring=False):
        q, seen = deque([start]), {start}
        while q:
            x, y = q.popleft()
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                p = (x+dx, y+dy)
                if 0<=p[0]<cols and 0<=p[1]<rows and p not in seen and p not in body_set and p not in mines:
                    if avoid_ring and (p[0]==0 or p[0]==cols-1 or p[1]==0 or p[1]==rows-1): continue
                    seen.add(p)
                    q.append(p)
        return len(seen)

    # ==========================================================
    # HAMILTONIAN FALLBACK
    # ==========================================================
    def get_hamiltonian_move(self, juego):
        cols, rows = juego.casillas_x, juego.casillas_y
        head = juego.snake.cuerpo[-1]
        body = set(juego.snake.cuerpo)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            p = (head[0]+dx, head[1]+dy)
            if 0<=p[0]<cols and 0<=p[1]<rows and p not in body:
                return (dx, dy)
        return juego.snake.direccion
    
    def finalize_game(self, won: bool):
        pass