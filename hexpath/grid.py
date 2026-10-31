"""Grid model: weighted terrain, obstacles, start/goal.

Cost 0 means impassable. Terrain costs: plains 1, forest 2, swamp 3, mountain 4.
"""

import random

from .hexgrid import neighbors as _hex_neighbors

TERRAIN_NAMES: list[str] = ["plains", "forest", "swamp", "mountain"]
TERRAIN_COST: dict[str, int] = {"plains": 1, "forest": 2, "swamp": 3, "mountain": 4}
TERRAIN_WEIGHTS: list[int] = [50, 25, 15, 10]
OBSTACLE_COST = 0

MAX_ROWS = 120
MAX_COLS = 120


class Grid:
    def __init__(self, rows: int, cols: int):
        if not 1 <= rows <= MAX_ROWS or not 1 <= cols <= MAX_COLS:
            raise ValueError(f"rows/cols must be within 1..{MAX_ROWS}/{MAX_COLS}")
        self.rows = rows
        self.cols = cols
        self.cost = [[1] * cols for _ in range(rows)]
        self.start = (0, 0)
        self.goal = (cols - 1, rows - 1)

    def in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    def cost_at(self, col: int, row: int) -> int:
        return self.cost[row][col]

    def passable(self, col: int, row: int) -> bool:
        return self.cost_at(col, row) > 0

    def neighbors(self, col: int, row: int) -> list[tuple[int, int]]:
        """In-bounds, passable neighbors in AX_DIRS order."""
        return [n for n in _hex_neighbors(col, row, self.cols, self.rows)
                if self.passable(*n)]

    def set_start(self, col: int, row: int) -> None:
        if not self.in_bounds(col, row):
            return
        self.start = (col, row)
        self.cost[row][col] = 1

    def set_goal(self, col: int, row: int) -> None:
        if not self.in_bounds(col, row):
            return
        self.goal = (col, row)
        self.cost[row][col] = 1

    def paint_obstacle(self, col: int, row: int) -> None:
        """Set a tile impassable; start/goal are never obstacles."""
        if not self.in_bounds(col, row) or (col, row) == self.start or (col, row) == self.goal:
            return
        self.cost[row][col] = OBSTACLE_COST

    def erase_obstacle(self, col: int, row: int) -> None:
        """Make a tile plains; start/goal are never obstacles."""
        if not self.in_bounds(col, row) or (col, row) == self.start or (col, row) == self.goal:
            return
        self.cost[row][col] = 1

    def clear_map(self) -> None:
        for row in range(self.rows):
            for col in range(self.cols):
                self.cost[row][col] = 1

    def generate_random(self, rng: random.Random, density: int) -> None:
        """Obstacles at `density` percent, then weighted terrain on the rest.

        Start and goal are forced passable (cost 1), so algorithms never see a blocked
        endpoint.
        """
        density = max(0, min(60, density))
        for row in range(self.rows):
            for col in range(self.cols):
                if rng.random() < density / 100.0:
                    self.cost[row][col] = OBSTACLE_COST
                else:
                    name = rng.choices(TERRAIN_NAMES, weights=TERRAIN_WEIGHTS)[0]
                    self.cost[row][col] = TERRAIN_COST[name]
        self.cost[self.start[1]][self.start[0]] = 1
        self.cost[self.goal[1]][self.goal[0]] = 1
