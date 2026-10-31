"""Step-indexed trace: one run recorded once, playback is index arithmetic.

`step` is the number of expansions already executed (0 .. total_steps). Rendering at
step `i` is a pure function of the trace, so forward/back/scrub/auto are integer moves
of one index. No snapshots, no re-runs.
"""

from dataclasses import dataclass

INF = 10 ** 9


@dataclass
class Trace:
    algo: str
    steps: list[tuple[int, int]]
    discovered_at: dict[tuple[int, int], int]
    visited_at: dict[tuple[int, int], int]
    side: dict[tuple[int, int], str]
    found: bool
    path: list[tuple[int, int]] | None
    cost: int | None
    exhausted: bool

    def total_steps(self) -> int:
        return len(self.steps)

    def classify(self, tile: tuple[int, int], step: int, grid) -> str:
        """Exactly one of 'current', 'path', 'visited_S', 'visited_G',
        'frontier_S', 'frontier_G', 'obstacle', 'terrain' — top-to-bottom priority.

        Frontier reconstruction needs no removal events: a tile is frontier at `step`
        when it has been discovered by expansion `step` or earlier and is not expanded
        yet — the open set as the algorithm sees it after `step` expansions, which
        covers lazy-deletion heaps. `step > 0` keeps step 0 free of frontier tiles.
        """
        if step > 0 and self.steps[step - 1] == tile:
            return "current"
        if self.found and step == self.total_steps() and tile in self.path:
            return "path"
        d = self.discovered_at.get(tile, INF)
        v = self.visited_at.get(tile, INF)
        if v < step:
            return "visited_" + self.side[tile]
        if step > 0 and d <= step and v >= step:
            return "frontier_" + self.side[tile]
        if grid.cost_at(*tile) == 0:
            return "obstacle"
        return "terrain"
