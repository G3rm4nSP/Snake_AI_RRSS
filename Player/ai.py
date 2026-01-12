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
                if grid[p.row][p.column] in (0, 4):
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
    def find_path(grid, head_pos, tail_pos, food_pos):
        path = StarPathfinder._find_path_to(
            grid, head_pos, tail_pos, food_pos
        )
        if path == "NOT_FOUND":
            path = StarPathfinder._find_path_to(
                grid, head_pos, tail_pos, tail_pos
            )
        return path

    @staticmethod
    def _find_path_to(grid, head_pos, tail_pos, target_pos):
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

                if cell == 0 or (cell == 3 and target == tail) or cell == 4:
                    neighbor = NodeBase(p)
                    if neighbor in processed:
                        continue

                    cost = current.g + 1
                    if neighbor not in to_search or cost < neighbor.g:
                        neighbor.g = cost
                        neighbor.h = Distance.manhattan(
                            neighbor.position, target.position
                        )
                        neighbor.connection = current
                        if neighbor not in to_search:
                            to_search.append(neighbor)


# =========================
# Player logic
# =========================

class StarPlayer:

    @staticmethod
    def decide(data, snake_go_to):
        rows = len(data.grid)
        columns = len(data.grid[0])

        percentage = data.snake_size / (rows * columns)

        directions = StarExtensions.get_star_directions(
            data.head_position, rows, columns
        )

        options = [
            data.head_position.move_to(d)
            for d in directions
            if data.grid[
                data.head_position.move_to(d).row
            ][
                data.head_position.move_to(d).column
            ] == 0
        ]

        if percentage > 0.25 and len(options) == 2:
            counts = []
            for option in options:
                data.grid[option.row][option.column] = CellType.SnakeBody.value
                count = StarEmptyCounter.run(data.grid, option)
                counts.append(count)
                data.grid[option.row][option.column] = CellType.Empty.value

            if counts[1] > counts[0]:
                snake_go_to(directions[1])
                return StarExtensions.direction_to_char(directions[1])
            if counts[0] > counts[1]:
                snake_go_to(directions[0])
                return StarExtensions.direction_to_char(directions[0])

        path = StarPathfinder.find_path(
            data.grid,
            data.head_position,
            data.tail_position,
            data.food_position
        )

        first_dir = StarExtensions.char_to_direction(path[0])
        snake_go_to(first_dir)
        return path
