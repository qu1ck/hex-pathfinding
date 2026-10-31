"""Grid model: seeded generation, start/goal protection, clear_map, neighbor filtering."""

import random

from hexpath.grid import Grid, OBSTACLE_COST, TERRAIN_COST


def seeded_grid(seed: int, rows: int, cols: int, density: int) -> Grid:
    grid = Grid(rows, cols)
    grid.generate_random(random.Random(seed), density)
    return grid


def test_default_grid_is_all_plains():
    grid = Grid(4, 6)
    assert grid.rows == 4 and grid.cols == 6
    assert grid.start == (0, 0)
    assert grid.goal == (5, 3)
    assert all(grid.cost_at(col, row) == 1 for row in range(4) for col in range(6))
    assert grid.passable(0, 0) and grid.passable(5, 3)


def test_seeded_density_close_to_20_percent():
    """random.Random(1) at density 20 on a 40x40 grid gives 0.18875 obstacle fraction."""
    grid = seeded_grid(1, 40, 40, 20)
    total = 40 * 40
    obstacles = sum(1 for row in range(40) for col in range(40)
                    if grid.cost_at(col, row) == OBSTACLE_COST)
    fraction = obstacles / total
    assert fraction == 0.18875
    assert 0.16 <= fraction <= 0.24          # within 20% +/- 4


def test_seeded_costs_are_valid_terrain_values():
    grid = seeded_grid(1, 40, 40, 20)
    allowed = set(TERRAIN_COST.values()) | {OBSTACLE_COST}
    costs = {grid.cost_at(col, row) for row in range(40) for col in range(40)}
    assert costs <= allowed
    assert costs == allowed                  # all four terrain levels appear, plus obstacles


def test_start_and_goal_forced_passable():
    grid = seeded_grid(1, 40, 40, 60)     # density 60: the endpoints are forced to plains
    assert grid.cost_at(*grid.start) == 1
    assert grid.cost_at(*grid.goal) == 1
    assert grid.passable(*grid.start) and grid.passable(*grid.goal)


def test_paint_and_erase_are_no_ops_on_start_and_goal():
    grid = seeded_grid(1, 40, 40, 20)
    grid.paint_obstacle(*grid.start)
    grid.paint_obstacle(*grid.goal)
    assert grid.cost_at(*grid.start) == 1
    assert grid.cost_at(*grid.goal) == 1
    grid.erase_obstacle(*grid.start)
    grid.erase_obstacle(*grid.goal)
    assert grid.cost_at(*grid.start) == 1
    assert grid.cost_at(*grid.goal) == 1


def test_paint_and_erase_work_on_plain_tiles():
    grid = Grid(5, 5)
    grid.paint_obstacle(2, 2)
    assert grid.cost_at(2, 2) == OBSTACLE_COST
    assert not grid.passable(2, 2)
    grid.erase_obstacle(2, 2)
    assert grid.cost_at(2, 2) == 1
    # out-of-bounds calls change nothing
    grid.paint_obstacle(9, 9)
    grid.erase_obstacle(-1, 0)
    assert all(grid.cost_at(col, row) == 1 for row in range(5) for col in range(5))


def test_clear_map_makes_every_tile_plains():
    grid = seeded_grid(1, 40, 40, 20)
    grid.clear_map()
    assert all(grid.cost_at(col, row) == 1 for row in range(40) for col in range(40))


def test_neighbors_never_yield_an_obstacle():
    grid = seeded_grid(1, 40, 40, 20)
    for row in range(40):
        for col in range(40):
            for n in grid.neighbors(col, row):
                assert grid.passable(*n), ((col, row), n)
                assert grid.in_bounds(*n)


def test_moving_start_clears_the_tile():
    grid = seeded_grid(1, 20, 26, 20)
    grid.set_start(3, 4)
    assert grid.start == (3, 4)
    assert grid.cost_at(3, 4) == 1
    grid.set_goal(10, 12)
    assert grid.goal == (10, 12)
    assert grid.cost_at(10, 12) == 1
