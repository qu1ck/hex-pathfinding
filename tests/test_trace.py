"""classify(): the priority rules, frontier reconstruction, and side labels.

`step` counts the expansions already executed. A tile discovered during the expansion
that produced step index k has discovered_at == k, so it enters the visible frontier at
step k+1 (rule 4 is a strict `<`).
"""

from conftest import OPEN_MAP, make_grid
from hexpath.algorithms import ALGORITHMS

CLASSES = {"current", "path", "visited_S", "visited_G",
           "frontier_S", "frontier_G", "obstacle", "terrain"}
SIDES = {"S", "G"}
OBSTACLE_TILES = [(3, 0), (3, 1)]


def all_tiles(grid):
    return [(col, row) for row in range(grid.rows) for col in range(grid.cols)]


def classes_at(trace, grid, step):
    return {tile: trace.classify(tile, step, grid) for tile in all_tiles(grid)}


def counts(classes, prefix):
    return sum(1 for value in classes.values() if value.startswith(prefix))


def open_map_trace(algo: str):
    grid = make_grid(OPEN_MAP)
    return grid, ALGORITHMS[algo](grid)


def test_total_steps_is_the_length_of_steps():
    grid, trace = open_map_trace("A*")
    assert trace.total_steps() == len(trace.steps) == 12


def test_step_zero_is_pure_terrain_and_obstacles():
    """Rules 1 and 4 both require step > 0, so step 0 has no frontier and no current tile."""
    grid, trace = open_map_trace("A*")
    classes = classes_at(trace, grid, 0)
    assert all(value in ("terrain", "obstacle") for value in classes.values())
    assert counts(classes, "frontier") == 0
    assert counts(classes, "visited") == 0
    assert counts(classes, "path") == 0
    assert "current" not in classes.values()
    for tile in OBSTACLE_TILES:
        assert classes[tile] == "obstacle"
    assert classes[grid.start] == "terrain"


def test_step_one_marks_the_first_expansion_current():
    grid, trace = open_map_trace("A*")
    classes = classes_at(trace, grid, 1)
    first = trace.steps[0]
    assert first == grid.start
    assert classes[first] == "current"
    # the passable neighbours of steps[0] are discovered by the step-1 expansion, so they
    # are the frontier at step 1 — the open set right after the pick.
    neighbours = grid.neighbors(*first)
    assert all(classes[n] == "frontier_S" for n in neighbours), (first, neighbours)
    assert all(trace.side[n] == "S" for n in neighbours)


def test_step_two_shows_the_start_frontier():
    """One step later, the passable neighbours of steps[0] are on the S-side frontier."""
    grid, trace = open_map_trace("A*")
    classes = classes_at(trace, grid, 2)
    assert classes[grid.start] == "visited_S"
    neighbours = grid.neighbors(*grid.start)
    assert all(classes[n] in ("frontier_S", "visited_S", "current") for n in neighbours)
    frontier = [n for n in neighbours if classes[n] == "frontier_S"]
    assert frontier, "the start's frontier must appear one step after its expansion"
    assert all(trace.side[n] == "S" for n in neighbours)


def test_no_path_tiles_before_the_final_step():
    grid, trace = open_map_trace("A*")
    classes = classes_at(trace, grid, trace.total_steps() - 1)
    assert "path" not in classes.values()


def test_final_step_shows_the_path_and_the_goal_current():
    grid, trace = open_map_trace("A*")
    total = trace.total_steps()
    classes = classes_at(trace, grid, total)
    assert classes[grid.goal] == "current"          # rule 1 wins over rule 2
    path_tiles = [t for t in trace.path if t != grid.goal]
    assert len(path_tiles) == 7
    assert all(classes[t] == "path" for t in path_tiles)
    assert counts(classes, "path") == 7


def test_classify_always_returns_a_known_class():
    grid, trace = open_map_trace("A*")
    for step in range(trace.total_steps() + 1):
        for value in classes_at(trace, grid, step).values():
            assert value in CLASSES, (step, value)


def test_obstacles_are_never_in_the_trace():
    grid, trace = open_map_trace("A*")
    touched = set(trace.steps) | set(trace.discovered_at)
    for tile in OBSTACLE_TILES:
        assert tile not in touched
        for step in range(trace.total_steps() + 1):
            assert trace.classify(tile, step, grid) == "obstacle"


def test_frontier_count_never_grows_as_the_end_approaches():
    """Frontiers grow while the search spreads, then shrink monotonically toward `total`."""
    grid, trace = open_map_trace("A*")
    total = trace.total_steps()
    frontier_counts = [counts(classes_at(trace, grid, step), "frontier")
                       for step in range(total + 1)]
    assert frontier_counts[0] == 0
    peak = max(range(total + 1), key=lambda step: frontier_counts[step])
    tail = frontier_counts[peak:]
    assert all(tail[i] >= tail[i + 1] for i in range(len(tail) - 1))
    assert tail[-1] <= tail[0]


def test_bidirectional_trace_uses_both_sides():
    grid, trace = open_map_trace("Bidirectional BFS")
    total = trace.total_steps()
    assert set(trace.side.values()) == SIDES
    assert trace.side[grid.start] == "S"
    assert trace.side[grid.goal] == "G"
    seen: set[str] = set()
    for step in range(total + 1):
        seen |= set(classes_at(trace, grid, step).values())
    for wanted in ("frontier_S", "frontier_G", "visited_S", "visited_G"):
        assert wanted in seen, wanted
    assert counts(classes_at(trace, grid, 0), "frontier") == 0
    for tile, side in trace.side.items():
        assert side in SIDES, tile
