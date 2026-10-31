"""Algorithms on ASCII fixtures, plus determinism, visited_at indexing, and the big-map reference.

Every expected number below was measured against the real implementation, so the fixtures
act as a regression lock on the tie-break/pop rules (goal-at-pop, push_counter FIFO ties).
"""

import random

import pytest

from conftest import BLOCKED_MAP, OPEN_MAP, make_grid
from hexpath.algorithms import ALGORITHMS, COMBO_CHOICES
from hexpath.grid import Grid

ALL_ALGOS = list(ALGORITHMS)
SINGLE_SOURCE = [a for a in ALL_ALGOS if a != "Bidirectional BFS"]
NON_OPTIMAL = ["DFS", "Greedy Best-First", "Weighted A* (w=3)"]
OPTIMAL_COST = 7
EXPECTED_PATH = [(0, 0), (1, 0), (2, 0), (2, 1), (3, 2), (4, 2), (4, 1), (4, 0)]


def seeded_grid(seed: int = 7, rows: int = 20, cols: int = 26, density: int = 20) -> Grid:
    grid = Grid(rows, cols)
    grid.generate_random(random.Random(seed), density)
    return grid


def test_combo_choices_are_the_registry_labels():
    assert COMBO_CHOICES == ["BFS", "DFS", "Dijkstra", "A*",
                             "Greedy Best-First", "Weighted A* (w=3)", "Bidirectional BFS"]


def path_is_valid(grid, path):
    assert path, "path must be non-empty"
    assert path[0] == grid.start
    assert path[-1] == grid.goal
    for tile in path:
        assert grid.cost_at(*tile) > 0, tile
    for a, b in zip(path, path[1:]):
        assert b in grid.neighbors(*a), (a, b)


@pytest.mark.parametrize("algo", ALL_ALGOS)
def test_open_map_every_algorithm_finds_a_valid_path(algo):
    grid = make_grid(OPEN_MAP)
    trace = ALGORITHMS[algo](grid)
    assert trace.found is True
    assert trace.exhausted is False
    assert trace.algo == algo
    path_is_valid(grid, trace.path)
    assert len(trace.path) == 8


@pytest.mark.parametrize("algo", [a for a in ALL_ALGOS if a != "DFS"])
def test_open_map_expected_path(algo):
    """BFS, Dijkstra, A*, Greedy, Weighted A*, and Bidirectional BFS all return this path."""
    grid = make_grid(OPEN_MAP)
    trace = ALGORITHMS[algo](grid)
    assert trace.path == EXPECTED_PATH


@pytest.mark.parametrize("algo", ["Dijkstra", "A*", "BFS", "Bidirectional BFS"])
def test_open_map_optimal_cost_is_7(algo):
    grid = make_grid(OPEN_MAP)
    trace = ALGORITHMS[algo](grid)
    assert trace.cost == OPTIMAL_COST


@pytest.mark.parametrize("algo", NON_OPTIMAL)
def test_open_map_non_optimal_algorithms_still_pay_at_least_7(algo):
    grid = make_grid(OPEN_MAP)
    trace = ALGORITHMS[algo](grid)
    assert trace.cost >= OPTIMAL_COST


def test_open_map_step_counts():
    grid = make_grid(OPEN_MAP)
    assert ALGORITHMS["Dijkstra"](grid).total_steps() == 13
    assert ALGORITHMS["A*"](grid).total_steps() == 12
    assert ALGORITHMS["BFS"](grid).total_steps() == 13


@pytest.mark.parametrize("algo", ALL_ALGOS)
def test_blocked_map_is_unsolvable_for_every_algorithm(algo):
    grid = make_grid(BLOCKED_MAP)
    trace = ALGORITHMS[algo](grid)
    assert trace.found is False
    assert trace.path is None
    assert trace.cost is None
    assert trace.exhausted is True


@pytest.mark.parametrize("algo", SINGLE_SOURCE)
def test_blocked_map_single_source_expands_9_tiles(algo):
    grid = make_grid(BLOCKED_MAP)
    assert ALGORITHMS[algo](grid).total_steps() == 9


def test_blocked_map_bidirectional_expands_12_tiles():
    """Bidirectional BFS covers the 9-tile start component and the 3-tile goal component."""
    grid = make_grid(BLOCKED_MAP)
    trace = ALGORITHMS["Bidirectional BFS"](grid)
    assert trace.total_steps() == 12


@pytest.mark.parametrize("algo", ALL_ALGOS)
def test_start_equal_goal_is_trivial(algo):
    grid = make_grid(OPEN_MAP)
    grid.set_goal(*grid.start)
    trace = ALGORITHMS[algo](grid)
    assert trace.steps == [grid.start]
    assert trace.found is True
    assert trace.cost == 0
    assert trace.path == [grid.start]
    assert trace.exhausted is False


@pytest.mark.parametrize("algo", ALL_ALGOS)
def test_traces_are_deterministic(algo):
    grid = seeded_grid()
    first = ALGORITHMS[algo](grid)
    second = ALGORITHMS[algo](grid)
    assert first.steps == second.steps
    assert first.path == second.path
    assert first.cost == second.cost


@pytest.mark.parametrize("algo", ALL_ALGOS)
def test_visited_at_indexes_the_steps_list(algo):
    grid = seeded_grid()
    trace = ALGORITHMS[algo](grid)
    values = sorted(trace.visited_at.values())
    assert values == list(range(len(trace.steps)))
    for tile, index in trace.visited_at.items():
        assert trace.steps[index] == tile


def test_big_map_reference_numbers():
    """Rows 20, cols 26, seed 7, density 20: measured expansions, optimal cost, path length."""
    grid = seeded_grid(7, 20, 26, 20)
    bfs = ALGORITHMS["BFS"](grid)
    dijkstra = ALGORITHMS["Dijkstra"](grid)
    astar = ALGORITHMS["A*"](grid)
    dfs = ALGORITHMS["DFS"](grid)
    for trace in (bfs, dijkstra, astar, dfs):
        assert trace.found is True
        path_is_valid(grid, trace.path)
    assert bfs.total_steps() == 401
    assert dijkstra.total_steps() == 400
    assert astar.total_steps() == 332
    assert astar.total_steps() <= dijkstra.total_steps()   # A* never expands more than Dijkstra
    assert bfs.cost == dijkstra.cost == astar.cost == 48
    assert len(bfs.path) == len(dijkstra.path) == len(astar.path) == 38
    assert dfs.cost > 48
