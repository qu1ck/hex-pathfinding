"""Pathfinding algorithms that record a step-indexed Trace.

Single-source template: goal-at-pop stop, lazy-deletion heaps (no removal events),
`push_counter` strictly increasing so equal keys pop in insertion order. Traces are
deterministic on a fixed grid, which is what makes playback reproducible.
"""

import heapq
from collections import deque

from .hexgrid import hex_distance
from .trace import Trace

W = 3  # heuristic weight for Weighted A*


def parent_chain(parent: dict, tile: tuple[int, int]) -> list[tuple[int, int]]:
    """Walk `parent` from tile to the root; returns tile..start."""
    chain: list[tuple[int, int]] = []
    while tile is not None:
        chain.append(tile)
        tile = parent.get(tile)
    return chain


def _finish(grid, name, steps, discovered_at, visited_at, side, found, parent, exhausted):
    path: list[tuple[int, int]] | None = None
    cost: int | None = None
    if found:
        path = list(reversed(parent_chain(parent, grid.goal)))
        cost = sum(grid.cost_at(*t) for t in path[1:])
    return Trace(algo=name, steps=steps, discovered_at=discovered_at, visited_at=visited_at,
                side=side, found=found, path=path, cost=cost, exhausted=exhausted)


def _search(grid, name: str, kind: str) -> Trace:
    start, goal = grid.start, grid.goal
    g: dict[tuple[int, int], int] = {start: 0}
    parent: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    discovered_at = {start: 0}
    side = {start: "S"}
    visited_at: dict[tuple[int, int], int] = {}
    steps: list[tuple[int, int]] = []
    push_counter = 0

    if kind == "bfs":
        frontier: deque[tuple[int, int]] = deque([start])
        def push(tile, ng):
            frontier.append(tile)
        def pop():
            return frontier.popleft()
    elif kind == "dfs":
        frontier: list[tuple[int, int]] = [start]
        def push(tile, ng):
            frontier.append(tile)
        def pop():
            return frontier.pop()
    else:
        if kind == "dijkstra":
            key = lambda ng, tile: ng
        elif kind == "astar":
            key = lambda ng, tile: ng + hex_distance(tile, goal)
        elif kind == "greedy":
            key = lambda ng, tile: hex_distance(tile, goal)
        elif kind == "wastar":
            key = lambda ng, tile: ng + W * hex_distance(tile, goal)
        frontier = [(key(0, start), 0, start[0], start[1])]
        def push(tile, ng):
            nonlocal push_counter
            push_counter += 1
            heapq.heappush(frontier, (key(ng, tile), push_counter, tile[0], tile[1]))
        def pop():
            entry = heapq.heappop(frontier)
            return (entry[2], entry[3])

    while frontier:
        t = pop()
        if t in visited_at:
            continue  # lazy skip for heap algorithms
        visited_at[t] = len(steps)
        steps.append(t)
        if t == goal:
            return _finish(grid, name, steps, discovered_at, visited_at, side, True, parent, False)
        for n in grid.neighbors(*t):
            if n in visited_at:
                continue
            ng = g[t] + grid.cost_at(*n)
            if n not in g or ng < g[n]:
                g[n] = ng
                parent[n] = t
                push_counter += 1
                if n not in discovered_at:
                    discovered_at[n] = len(steps)
                    side[n] = "S"
                push(n, ng)
    return _finish(grid, name, steps, discovered_at, visited_at, side, False, parent, True)


def bfs(grid) -> Trace:
    return _search(grid, "BFS", "bfs")


def dfs(grid) -> Trace:
    return _search(grid, "DFS", "dfs")


def dijkstra(grid) -> Trace:
    return _search(grid, "Dijkstra", "dijkstra")


def astar(grid) -> Trace:
    return _search(grid, "A*", "astar")


def greedy_best_first(grid) -> Trace:
    return _search(grid, "Greedy Best-First", "greedy")


def weighted_astar(grid) -> Trace:
    return _search(grid, "Weighted A* (w=3)", "wastar")


def bidirectional_bfs(grid) -> Trace:
    """Two frontiers, unit edge cost (terrain weights ignored, as in plain BFS).

    Each step pops exactly one tile, from the smaller frontier; ties go to 'S'. A pop
    that lands on a tile discovered by the other side is the meeting point.
    """
    start, goal = grid.start, grid.goal
    front_s = deque([start])
    front_g = deque([goal])
    parent_s: dict = {start: None}
    parent_g: dict = {goal: None}
    discovered_at: dict[tuple[int, int], int] = {start: 0, goal: 0}
    side = {start: "S", goal: "G"}
    visited_at: dict[tuple[int, int], int] = {}
    steps: list[tuple[int, int]] = []
    path: list[tuple[int, int]] | None = None

    while front_s or front_g:
        use_s = len(front_s) <= len(front_g) if front_g and front_s else bool(front_s)
        frontier = front_s if use_s else front_g
        me = "S" if use_s else "G"
        my_parent = parent_s if use_s else parent_g
        other_parent = parent_g if use_s else parent_s
        t = frontier.popleft()
        if t in visited_at:
            continue
        visited_at[t] = len(steps)
        steps.append(t)
        if side[t] != me:
            path = list(reversed(parent_chain(my_parent, t))) + parent_chain(other_parent, t)[1:]
            if path[0] != start:
                path.reverse()  # the meeting pop can come from the goal side
            cost = sum(grid.cost_at(*x) for x in path[1:])
            return Trace(algo="Bidirectional BFS", steps=steps, discovered_at=discovered_at,
                         visited_at=visited_at, side=side, found=True, path=path, cost=cost,
                         exhausted=False)
        for n in grid.neighbors(*t):
            if n in visited_at:
                continue
            if n not in discovered_at:
                discovered_at[n] = len(steps)
                side[n] = me
            frontier.append(n)
            if n not in my_parent:
                my_parent[n] = t
    return Trace(algo="Bidirectional BFS", steps=steps, discovered_at=discovered_at,
                 visited_at=visited_at, side=side, found=False, path=None, cost=None,
                 exhausted=True)


ALGORITHMS: dict[str, callable] = {
    "BFS": bfs,
    "DFS": dfs,
    "Dijkstra": dijkstra,
    "A*": astar,
    "Greedy Best-First": greedy_best_first,
    "Weighted A* (w=3)": weighted_astar,
    "Bidirectional BFS": bidirectional_bfs,
}
COMBO_CHOICES: list[str] = list(ALGORITHMS)
