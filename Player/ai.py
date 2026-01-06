import heapq
import json
import os
import random
from collections import deque, defaultdict


class PlayerAI:
    def __init__(self):
        self.memory = deque(maxlen=50)
        self.body_length_memory = 0

        self.knowledge_file = "snake_ai_knowledge.json"
        self.knowledge = defaultdict(lambda: defaultdict(int))

        self.generation = 1
        self.steps_alive = 0

        self.load_knowledge()

    # ==========================================================
    # PERSISTENCIA
    # ==========================================================
    def load_knowledge(self):
        if os.path.exists(self.knowledge_file):
            with open(self.knowledge_file, "r") as f:
                raw = json.load(f)
                for k, v in raw.items():
                    self.knowledge[k] = defaultdict(int, v)
            print(f"[AI] Conocimiento cargado ({len(self.knowledge)})")
        else:
            print("[AI] Nueva IA, sin conocimiento previo")

    def save_knowledge(self):
        with open(self.knowledge_file, "w") as f:
            json.dump(self.knowledge, f)

    def on_game_over(self):
        self.save_knowledge()
        self.generation += 1
        self.steps_alive = 0
        print(f"[AI] Nueva generación → {self.generation}")

    # ==========================================================
    # MAIN
    # ==========================================================
    def get_next_move(self, juego):
        self.steps_alive += 1

        head = juego.snake.cuerpo[-1]
        body = list(juego.snake.cuerpo)
        tail = body[0]
        body_set = set(body)
        fruits = set(juego.frutas)
        mines = set(juego.minas)
        cols, rows = juego.casillas_x, juego.casillas_y

        # -------- memoria para detectar bucle --------
        if self.body_length_memory != len(body):
            self.memory.clear()
            self.body_length_memory = len(body)

        self.memory.append(head)
        in_loop = len(self.memory) == self.memory.maxlen and len(set(self.memory)) < 5

        # -------- estado IA --------
        state = self.make_state(
            head, fruits, body, mines, cols, rows, in_loop
        )
        state_key = str(state)

        # ==================================================
        # 1️⃣ ALGORITMO NORMAL (SIEMPRE)
        # ==================================================
        move = None

        if fruits:
            move = self.move_to_fruit(head, body, tail, fruits, mines, cols, rows)

        if not move:
            move = self.follow_tail(head, tail, body_set, mines, cols, rows)

        if not move:
            move = self.get_safe_random(head, body_set, mines, cols, rows)

        # ==================================================
        # 2️⃣ APRENDIZAJE DEL ALGORITMO
        # ==================================================
        if move:
            self.knowledge[state_key][str(move)] += 1

        # ==================================================
        # 3️⃣ SI ENTRA EN BUCLE → USAR IA
        # ==================================================
        if in_loop:
            learned = self.choose_learned_action(state_key, head, body_set, mines, cols, rows)
            if learned:
                return learned
            else:
                return self.break_loop_random(head, body_set, mines, cols, rows)

        return move or juego.snake.direccion

    # ==========================================================
    # IA APRENDIDA
    # ==========================================================
    def choose_learned_action(self, state_key, head, body_set, mines, cols, rows):
        if state_key not in self.knowledge:
            return None

        actions = sorted(
            self.knowledge[state_key].items(),
            key=lambda x: x[1],
            reverse=True
        )

        for action_str, _ in actions:
            dx, dy = eval(action_str)
            nx, ny = head[0] + dx, head[1] + dy
            if 0 <= nx < cols and 0 <= ny < rows:
                if (nx, ny) not in body_set and (nx, ny) not in mines:
                    return (dx, dy)
        return None

    # ==========================================================
    # ESTADO
    # ==========================================================
    def make_state(self, head, fruits, body, mines, cols, rows, in_loop):
        body_set = set(body)

        if fruits:
            fx, fy = min(fruits, key=lambda f: abs(f[0]-head[0]) + abs(f[1]-head[1]))
            dx, dy = fx - head[0], fy - head[1]
            dist = abs(dx) + abs(dy)
        else:
            dx = dy = dist = -1

        free_space = self.count_reachable(head, body_set, mines, cols, rows)

        blocked_x = int(any(
            (head[0] + i * (1 if dx > 0 else -1), head[1]) in body_set
            for i in range(1, abs(dx) + 1)
        )) if dx != 0 else 0

        blocked_y = int(any(
            (head[0], head[1] + i * (1 if dy > 0 else -1)) in body_set
            for i in range(1, abs(dy) + 1)
        )) if dy != 0 else 0

        return [
            dx, dy, dist,
            len(body),
            free_space,
            blocked_x,
            blocked_y,
            int(in_loop)
        ]

    # ==========================================================
    # MOVIMIENTOS
    # ==========================================================
    def move_to_fruit(self, head, body, tail, fruits, mines, cols, rows):
        body_set = set(body)
        for fruit in fruits:
            path = self.a_star(head, fruit, body_set, tail, mines, cols, rows)
            if path:
                nx, ny = path[0]
                return (nx - head[0], ny - head[1])
        return None

    def follow_tail(self, head, tail, body_set, mines, cols, rows):
        path = self.a_star(head, tail, body_set, tail, mines, cols, rows)
        if path:
            nx, ny = path[0]
            return (nx - head[0], ny - head[1])
        return None

    def break_loop_random(self, head, body_set, mines, cols, rows):
        dirs = [(-1,0),(1,0),(0,-1),(0,1)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = head[0]+dx, head[1]+dy
            if 0<=nx<cols and 0<=ny<rows and (nx,ny) not in body_set and (nx,ny) not in mines:
                return (dx, dy)
        return None

    def get_safe_random(self, head, body_set, mines, cols, rows):
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = head[0]+dx, head[1]+dy
            if 0<=nx<cols and 0<=ny<rows and (nx,ny) not in body_set and (nx,ny) not in mines:
                return (dx, dy)
        return None

    # ==========================================================
    # PATHFINDING
    # ==========================================================
    def a_star(self, start, goal, body, tail, mines, cols, rows):
        def h(a,b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
        frontier = [(0, start)]
        came = {start: None}
        cost = {start: 0}

        while frontier:
            _, cur = heapq.heappop(frontier)
            if cur == goal:
                break
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                nxt = (cur[0]+dx, cur[1]+dy)
                if not (0<=nxt[0]<cols and 0<=nxt[1]<rows): continue
                if nxt in body and nxt != tail: continue
                if nxt in mines: continue
                new_cost = cost[cur] + 1
                if nxt not in cost or new_cost < cost[nxt]:
                    cost[nxt] = new_cost
                    heapq.heappush(frontier, (new_cost + h(nxt, goal), nxt))
                    came[nxt] = cur

        if goal not in came:
            return None

        path = []
        cur = goal
        while cur != start:
            path.append(cur)
            cur = came[cur]
        path.reverse()
        return path

    def count_reachable(self, start, body, mines, cols, rows):
        q = deque([start])
        seen = {start}
        while q:
            x,y = q.popleft()
            for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                p = (x+dx, y+dy)
                if 0<=p[0]<cols and 0<=p[1]<rows:
                    if p not in seen and p not in body and p not in mines:
                        seen.add(p)
                        q.append(p)
        return len(seen)

    def finalize_game(self, won=False):
        """
        Llamado por el motor cuando la partida termina.
        """
        self.on_game_over()

# ==========================================================