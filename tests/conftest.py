"""Shared fixture helper: ASCII map rows -> Grid.

`make_grid` lives here so the algorithm/trace tests can share one fixture builder.
The tests directory is inserted on sys.path so `from conftest import make_grid` works
when pytest is run from the repo root as `python3 -m pytest tests -q`.
"""

import os
import sys

from hexpath.grid import Grid

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTS_DIR not in sys.path:
    sys.path.insert(0, TESTS_DIR)

# ASCII tokens: '.' plains 1, ',' forest 2, '~' swamp 3, '#' obstacle 0.
TOKEN_COST: dict[str, int] = {".": 1, ",": 2, "~": 3, "#": 0}

# 3 rows x 5 cols; column 3 is an obstacle wall, so the path must detour through row 2.
OPEN_MAP: list[str] = ["S . . # E", ", , . # .", ". . . . ."]

# Same map with the bottom-right gap closed: the start component is 9 tiles, the goal
# component 3 tiles, so no algorithm can reach the goal.
BLOCKED_MAP: list[str] = ["S . . # E", ", , . # .", ". . . # ."]


def make_grid(rows: list[str]) -> Grid:
    """Build a Grid from space-separated ASCII rows; rows[0] is the top row."""
    grid = Grid(len(rows), len(rows[0].split()))
    for row, line in enumerate(rows):
        for col, token in enumerate(line.split()):
            if token == "S":
                grid.set_start(col, row)      # forces cost 1
            elif token == "E":
                grid.set_goal(col, row)       # forces cost 1
            else:
                grid.cost[row][col] = TOKEN_COST[token]
    return grid
