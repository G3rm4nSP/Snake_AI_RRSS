import math
from enum import Enum
from collections import deque


# =========================
# Core structures
# =========================

class Direction(Enum):
    Up = (-1, 0)
    Right = (0, 1)
    Down = (1, 0)
    Left = (0, -1)


class CellType(Enum):
    Empty = 0
    Wall = 1
    Mine = 2
    SnakeBody = 3
    Food = 4


class Position:
    def __init__(self, row: int, column: int):
        self.row = row
        self.column = column

    def move_to(self, direction: Direction):
        dr, dc = direction.value
        return Position(self.row + dr, self.column + dc)

    def __eq__(self, other):
        return isinstance(other, Position) and \
               self.row == other.row and self.column == other.column

    def __hash__(self):
        return hash((self.row, self.column))


# =========================
# Distance helpers
# =========================

class Distance:
    @staticmethod
    def euclidian(a: Position, b: Position) -> float:
        return math.sqrt((a.row - b.row) ** 2 + (a.column - b.column) ** 2)

    @staticmethod
    def manhattan(a: Position, b: Position) -> int:
        return abs(a.row - b.row) + abs(a.column - b.column)


# =========================
# Node
# =========================

class NodeBase:
    def __init__(self, position: Position):
        self.position = position
        self.g = 0
        self.h = 0
        self.mines = 0
        self.connection = None
        self.neighbors = []

    @property
    def f(self):
        return self.g + self.h

    def get_direction(self):
        if self.connection is None:
            return ""

        if self.position.row < self.connection.position.row:
            return "U"
        if self.position.row > self.connection.position.row:
            return "D"
        if self.position.column < self.connection.position.column:
            return "L"
        return "R"

    def __eq__(self, other):
        return isinstance(other, NodeBase) and self.position == other.position

    def __hash__(self):
        return hash(self.position)


# =========================
# Star extensions
# =========================

class StarExtensions:

    @staticmethod
    def get_star_directions(position: Position, rows: int, columns: int):
        r, c = position.row, position.column

        if r % 2 == 0:
            if c % 2 == 0:
                if c == 0:
                    return [Direction.Down]
                return [Direction.Left, Direction.Down]
            if r == 0:
                return [Direction.Left]
            return [Direction.Left, Direction.Up]

        if c % 2 == 0:
            if r == rows - 1:
                return [Direction.Right]
            return [Direction.Right, Direction.Down]

        if c == columns - 1:
            return [Direction.Up]
        return [Direction.Up, Direction.Right]

    CHAR_TO_DIR = {
        'U': Direction.Up,
        'R': Direction.Right,
        'D': Direction.Down,
        'L': Direction.Left
    }

    DIR_TO_CHAR = {
        Direction.Up: 'U',
        Direction.Right: 'R',
        Direction.Down: 'D',
        Direction.Left: 'L'
    }

    @staticmethod
    def char_to_direction(value: str):
        return StarExtensions.CHAR_TO_DIR[value]

    @staticmethod
    def direction_to_char(direction: Direction):
        return StarExtensions.DIR_TO_CHAR[direction]


# =========================
# Empty space counter
# =========================

class StarEmptyCounter:

    @staticmethod
    def run(grid, start_position: Position):
        rows = len(grid)
        columns = len(grid[0])

        directions = [
            Direction.Right,
            Direction.Down,
            Direction.Left,
            Direction.Up
        ]

        neighbors = []
        for d in directions:
            p = start_position.move_to(d)
            if 0 <= p.row < rows and 0 <= p.column < columns:
                if grid[p.row][p.column] == CellType.Empty.value:
                    neighbors.append(NodeBase(p))

        minimum = float("inf")
        for n in neighbors:
            count = StarEmptyCounter._get_count(grid, n)
            minimum = min(minimum, count)

        return minimum

    @staticmethod
    def _get_count(grid, start_node: NodeBase):
        rows = len(grid)
        columns = len(grid[0])

        to_search = deque([start_node])
        processed = set()

        while True:
            if not to_search:
                return len(processed)

            if len(processed) >= rows + columns:
                return len(processed)

            current = to_search.popleft()
            processed.add(current)

            for d in [
                Direction.Right,
                Direction.Down,
                Direction.Left,
                Direction.Up
            ]:
                p = current.position.move_to(d)
                if 0 <= p.row < rows and 0 <= p.column < columns:
                    if grid[p.row][p.column] in (0, 4):
                        neighbor = NodeBase(p)
                        if neighbor not in processed and neighbor not in to_search:
                            to_search.append(neighbor)


# =========================
# A* Pathfinder
# =========================

class StarPathfinder:

    @staticmethod
    def find_path(grid, head_pos, tail_pos, foods, snake_body):
        # 1️⃣ Intentar ir a la comida
        path = StarPathfinder._best_food_path(
            grid, head_pos, tail_pos, foods, snake_body
        )

        # print("PATHFINDER FOOD PATH:", path)

        if path != "NOT_FOUND":
            return path

        # 2️⃣ Intentar seguir la cola
        path = StarPathfinder._find_path_to(
            grid, head_pos, tail_pos, tail_pos, snake_body
        )
        # print("PATHFINDER TAIL PATH:", path)

        if path != "NOT_FOUND":
            return path

        # 3️⃣ No hay camino seguro → generar Hamiltoniano parcial
        if snake_body:
            # Buscamos el "punto B" según tu lógica: desde la cola hacia la cabeza
            for pos in snake_body:
                if StarPathfinder._exists_path(grid, head_pos, pos):
                    h_path = StarPathfinder.hamiltonian_path(grid, head_pos, pos, snake_body)
                    return "".join([StarExtensions.direction_to_char(d) for d in h_path])

        # 4️⃣ Si no hay camino hacia ninguna parte → esperar (último recurso)
        return None

    def hamiltonian_path(grid, head_pos, target_pos, snake_body):
        """
        Genera un camino desde head_pos hasta target_pos intentando
        cubrir la mayor cantidad de casillas libres posibles.
        """
        rows, cols = len(grid), len(grid[0])
        visited = set(snake_body)  # posiciones ocupadas
        path = []
        stack = [(head_pos, [])]

        while stack:
            current, current_path = stack.pop()

            if current == target_pos:
                return current_path

            if current in visited:
                continue

            visited.add(current)
            for d in [Direction.Right, Direction.Down, Direction.Left, Direction.Up]:
                next_pos = current.move_to(d)
                if 0 <= next_pos.row < rows and 0 <= next_pos.column < cols:
                    if grid[next_pos.row][next_pos.column] in (0, 4) and next_pos not in visited:
                        stack.append((next_pos, current_path + [d]))

        # Si no se puede llegar a target_pos, devolvemos camino más largo posible
        return [d for d in current_path]
    @staticmethod
    def _exists_path(grid, start, end):
        """Verifica si hay un camino libre entre start y end."""
        rows, cols = len(grid), len(grid[0])
        visited = set()
        queue = deque([start])

        while queue:
            current = queue.popleft()
            if current == end:
                return True
            visited.add(current)
            for d in [Direction.Right, Direction.Down, Direction.Left, Direction.Up]:
                p = current.move_to(d)
                if 0 <= p.row < rows and 0 <= p.column < cols:
                    if grid[p.row][p.column] in (0, 4) and p not in visited:
                        queue.append(p)
        return False
    @staticmethod
    def _best_food_path(grid, head_pos, tail_pos, foods, snake_body):
        best = None
        best_score = float("inf")

        for food in foods:
            path = StarPathfinder._find_path_to(
                grid, head_pos, tail_pos, food, snake_body
            )

            if path == "NOT_FOUND":
                continue

            # score base = longitud
            score = len(path)

            if score < best_score:
                best_score = score
                best = path
        if best is None:
            return "NOT_FOUND"
        return best

    @staticmethod
    def _find_path_to(grid, head_pos, tail_pos, target_pos, snake_body):
        rows = len(grid)
        columns = len(grid[0])

        head = NodeBase(head_pos)
        tail = NodeBase(tail_pos)
        target = NodeBase(target_pos)

        to_search = [head]
        processed = set()

        while True:
            if not to_search:
                return "NOT_FOUND"

            current = min(
                to_search,
                key=lambda n: (n.f, n.h)
            )

            to_search.remove(current)
            processed.add(current)

            if current == target:
                path = ""
                node = current
                while node != head:
                    path += node.get_direction()
                    node = node.connection
                return path[::-1]

            directions = StarExtensions.get_star_directions(
                current.position, rows, columns
            )

            for d in directions:
                p = current.position.move_to(d)
                cell = grid[p.row][p.column]

                if cell in (
                    CellType.Empty.value,
                    CellType.Food.value,
                    CellType.Mine.value
                ) or (cell == CellType.SnakeBody.value and p == target.position):
                    neighbor = NodeBase(p)
                    if neighbor in processed:
                        continue

                    MINE_PENALTY = rows * columns + 1

                    if cell == CellType.Mine.value:
                        cost = current.g + MINE_PENALTY
                    else:
                        cost = current.g + 1

                    if neighbor not in to_search or cost < neighbor.g:
                        neighbor.g = cost
                        neighbor.h = Distance.manhattan(
                            neighbor.position, target.position
                        )
                        neighbor.mines = current.mines
                        if cell == CellType.Mine.value:
                            neighbor.mines += 1

                        neighbor.connection = current
                        if neighbor not in to_search:
                            to_search.append(neighbor)


# =========================
# Player logic
# =========================
class StarPlayer:

    @staticmethod
    def _simulate_snake_move(grid, snake_body, next_head, food_pos):
        """
        Devuelve un grid temporal donde la serpiente se mueve hacia next_head.
        Marca correctamente la cola si se va a comer fruta.
        """
        temp_grid = [row[:] for row in grid]
        body = snake_body[:]

        # agregamos la nueva cabeza
        body.append(next_head)
        if next_head == food_pos:
            # la serpiente come: la cola se queda
            for pos in body:
                temp_grid[pos.row][pos.column] = CellType.SnakeBody.value
        else:
            # la serpiente no come: eliminamos la cola
            tail = body.pop(0)
            for pos in body:
                temp_grid[pos.row][pos.column] = CellType.SnakeBody.value
            temp_grid[tail.row][tail.column] = CellType.Empty.value

        return temp_grid

    @staticmethod
    def decide(data, snake_go_to):
        rows = len(data.grid)
        columns = len(data.grid[0])
        snake_body = data.snake_body[:]  # lista de posiciones desde cola hasta cabeza

        directions = StarExtensions.get_star_directions(
            data.head_position, rows, columns
        )

        safe_options = []

        for d in directions:
            next_pos = data.head_position.move_to(d)
            cell = data.grid[next_pos.row][next_pos.column]
            
            if cell == CellType.Mine.value:
                continue

            if cell not in (
                CellType.Empty.value,
                CellType.Food.value,
                CellType.Mine.value
            ):
                continue

            # simulamos el movimiento completo
            temp_grid = StarPlayer._simulate_snake_move(data.grid, snake_body, next_pos, data.food_position)

            # verificamos si hay camino seguro a la cola
            path_to_tail = StarPathfinder._find_path_to(
                temp_grid, next_pos, data.tail_position, data.tail_position, snake_body
            )

            if path_to_tail != "NOT_FOUND":
                safe_options.append((d, next_pos))

        # =========================
        # Elegimos movimiento seguro
        # =========================
        if not safe_options:
            # No hay movimientos que mantengan camino a la cola → maximizamos espacio libre
            max_space = -1
            best_dir = directions[0]

            for d in directions:
                next_pos = data.head_position.move_to(d)
                cell = data.grid[next_pos.row][next_pos.column]
                if cell != 0 and cell != 4:
                    continue

                temp_grid = StarPlayer._simulate_snake_move(data.grid, snake_body, next_pos, data.food_position)
                empty_count = StarEmptyCounter.run(temp_grid, next_pos)

                if empty_count > max_space:
                    max_space = empty_count
                    best_dir = d

            snake_go_to(best_dir)
            return StarExtensions.direction_to_char(best_dir)

        # =========================
        # Si hay movimientos seguros → preferimos comida
        # =========================
        for d, pos in safe_options:
            if pos == data.food_position:
                snake_go_to(d)
                return StarExtensions.direction_to_char(d)

        # sino, cualquiera de los seguros
        snake_go_to(safe_options[0][0])
        return StarExtensions.direction_to_char(safe_options[0][0])
