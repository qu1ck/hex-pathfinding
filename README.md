# Hex Pathfinding Visualizer

Desktop app that visualizes pathfinding algorithms on a rectangular map of pointy-top
hexagon tiles with random obstacles and weighted terrain (plains 1, forest 2, swamp 3,
mountain 4; obstacles are impassable). The algorithm runs once and records a step-indexed
trace, so playback is pure index arithmetic: forward, back, scrub and auto play never
re-run the algorithm.

## Run

```
pip install -r requirements.txt      # wxPython>=4.2
python3 main.py                      # rows 20, cols 26, tile 28, seed 7, density 20
python3 main.py --rows 40 --cols 60 --tile 20 --seed 11 --density 30 --algo "Bidirectional BFS"
```

Headless helpers (run under `xvfb-run`): `--snapshot PATH` renders the canvas offscreen,
`--capture PATH` grabs the live frame; `--step INT` picks the rendered step,
`--exit-after MS` delays the capture.

## Controls (right panel)

- **Map**: rows, cols, tile size (px), "Apply size" — rebuilds the map. "Autosize" is a
  three-mode choice: **Off** keeps rows/cols/tile fixed; **Fit tile size** keeps rows/cols
  and refits the tile to the canvas on every resize (spin tracks the fitted value, map
  centered); **Fit map size** keeps the tile size from the spin and rebuilds rows/cols to
  fill the canvas — the grid regenerates from the seed and density, so the trace re-runs
  and the step resets to 0.
- **Random map**: obstacle density slider (0-60%), "Generate random map", "Clear map",
  "Randomize start/end".
- **Edit mode**: Draw obstacles / Erase obstacles / Set start / Set end. Left-drag paints
  the chosen action; right-click flips draw↔erase.
- **Algorithm**: BFS, DFS, Dijkstra, A*, Greedy Best-First, Weighted A* (w=3),
  Bidirectional BFS; "Auto-run on map change" checkbox; "Run".
- **Playback**: "← Back", "Forward", "Auto" toggle, speed slider (1-30 steps/sec), scrub
  slider, step counter. Auto play stops when it reaches the last step.
- **Legend**: terrain, obstacle, frontier/visited per side, current step, path tiles
  (purple) and the red path line with its black shadow.
- **Stats**: found, total cost, tiles expanded, path length.

## Keybindings

Space / Right — step forward · Backspace / Left — step back · A — toggle auto play ·
R — run algorithm · G — generate random map · C — clear map.

## Tests

```
xvfb-run -a -s "-screen 0 1280x1024x24 -extension GLX" python3 -m pytest tests -q
```
