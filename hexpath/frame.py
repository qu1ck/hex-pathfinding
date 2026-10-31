"""Main window: canvas on the left, control panel on the right, playback wiring.

The trace is computed once per map/algorithm; every playback action is one integer
move of `step`, never a re-run.
"""

import random

import wx

from .algorithms import ALGORITHMS
from .canvas import HexCanvas
from .controls import ControlPanel
from .grid import Grid


class MainFrame(wx.Frame):
    def __init__(self, rows, cols, tile_size, seed, density, algo):
        super().__init__(None, title="Hex Pathfinding Visualizer", size=(1200, 820))
        self.seed = seed
        self.density = density
        self.algo = algo
        self.tile_size = tile_size
        self.mode = "Draw obstacles"
        self.speed = 10
        self.scrub_guard = False
        self.step = 0
        self.trace = None
        self.build_grid(rows, cols)

        split = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_LIVE_UPDATE | wx.SP_3DSASH)
        self.canvas = HexCanvas(split, self.apply_tile_event, self._on_fit, self._on_fit_grid)
        self.controls = ControlPanel(split, self._handlers())
        # Negative sash position: the panel keeps 420 px, the canvas absorbs the rest.
        split.SplitVertically(self.canvas, self.controls, -420)
        split.SetSashGravity(1.0)
        split.SetMinimumPaneSize(320)
        self.controls.SetMinSize((380, 0))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(split, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_tick, self.timer)
        # Keys work from the frame and from the canvas (focus lands on the canvas after clicks).
        self.Bind(wx.EVT_KEY_DOWN, self.on_key)
        self.canvas.Bind(wx.EVT_KEY_DOWN, self.on_key)

        self.controls.algo_combo.SetValue(self.algo)
        self.canvas.set_map(self.grid, None, 0, self.tile_size)
        self.recompute()          # "Auto-run on map change" is checked by default
        self.Layout()
        self.Show()

    def _handlers(self) -> dict:
        return {
            "apply_map": self.apply_map,
            "random_map": self.random_map,
            "clear_map": self.clear_map,
            "random_start_end": self.random_start_end,
            "run": self.recompute,
            "step_forward": self.step_forward,
            "step_back": self.step_back,
            "auto_toggled": self.auto_toggled,
            "scrub": self.set_step,
            "set_algo": self.set_algo,
            "set_mode": self.set_mode,
            "set_speed": self.set_speed,
            "set_density": self.set_density,
            "set_autosize_mode": self.set_autosize_mode,
            "set_tile_size": self.set_tile_size,
        }

    # ---- state ----------------------------------------------------------------

    def total(self) -> int:
        return self.trace.total_steps() if self.trace is not None else 0

    def _update_labels(self) -> None:
        total = self.total()
        self.controls.set_step_labels(self.step, total)
        if self.trace is None:
            return
        cost_txt = str(self.trace.cost) if self.trace.cost is not None else "—"
        path_txt = str(len(self.trace.path)) if self.trace.path is not None else "—"
        self.controls.stats_label.SetLabel(
            f"Path found: {'yes' if self.trace.found else 'no'} | cost {cost_txt} "
            f"| tiles expanded {len(self.trace.steps)} | path length {path_txt}")

    def _sync_scrub(self) -> None:
        self.controls.scrub_guard = True
        self.controls.scrub_slider.SetValue(self.step)
        self.controls.scrub_guard = False

    def _repaint(self) -> None:
        self.canvas.set_map(self.grid, self.trace, self.step, self.tile_size)


    def _on_fit(self, tile: int) -> None:
        """Adopt the tile size the canvas fitted to its area, then repaint."""
        self.tile_size = tile
        self.controls.tile_spin.SetValue(tile)
        self._repaint()

    def set_autosize_mode(self, mode: str) -> None:
        self.canvas.autosize_mode = mode
        cw, ch = self.canvas.GetClientSize()
        if mode == "Fit tile size":
            self._on_fit(self.canvas.fit_tile(self.grid.cols, self.grid.rows, cw, ch))
        elif mode == "Fit map size":
            # The tile size is the user's in this mode, so take it from the spin.
            self.tile_size = self.controls.tile_spin.GetValue()
            self._refit_grid()

    def set_tile_size(self, tile: int) -> None:
        """Tile-size spin: "Fit map size" refits the grid, "Fit tile size" is pane-driven
        and applies through "Apply size"."""
        self.tile_size = max(10, min(80, int(tile)))
        if self.controls.tile_spin.GetValue() != self.tile_size:
            self.controls.tile_spin.SetValue(self.tile_size)   # keep the spin coherent
        if self.canvas.autosize_mode == "Fit map size":
            self._refit_grid()

    def _refit_grid(self) -> None:
        cw, ch = self.canvas.GetClientSize()
        cols, rows = self.canvas.fit_dims(self.tile_size, cw, ch)
        if (cols, rows) != (self.grid.cols, self.grid.rows):
            self._on_fit_grid(cols, rows)
        else:
            self._repaint()

    def _on_fit_grid(self, cols: int, rows: int) -> None:
        """Adopt the rows/cols fitted at the fixed tile size: rebuild the grid, re-run."""
        self.controls.rows_spin.SetValue(rows)
        self.controls.cols_spin.SetValue(cols)
        self.build_grid(rows, cols)
        self.canvas.set_map(self.grid, self.trace, 0, self.tile_size)
        self.on_map_changed()

    def build_grid(self, rows: int, cols: int) -> None:
        """Fresh grid: obstacles cleared, start (0,0), goal (cols-1, rows-1), terrain
        regenerated from the current seed and density."""
        self.grid = Grid(rows, cols)
        self.rng = random.Random(self.seed)
        self.grid.generate_random(self.rng, self.density)
        self.step = 0

    def recompute(self) -> None:
        self.trace = ALGORITHMS[self.algo](self.grid)
        self.step = 0
        total = self.trace.total_steps()
        self.controls.scrub_guard = True
        self.controls.scrub_slider.SetRange(0, total)
        self.controls.scrub_slider.SetValue(0)
        self.controls.scrub_guard = False
        self._update_labels()
        self._repaint()

    def on_map_changed(self) -> None:
        """After any grid edit: re-run when auto-run is on, otherwise keep the stale trace."""
        if self.controls.auto_run_check.GetValue():
            self.recompute()
        else:
            self._update_labels()
            self._repaint()

    def apply_tile_event(self, col, row, action) -> None:
        """Canvas action + current edit mode -> the grid operation."""
        mode = self.mode    # set_mode keeps this in sync with the panel RadioBox
        if action == "set_start" or mode == "Set start":
            self.grid.set_start(col, row)
        elif action == "set_goal" or mode == "Set end":
            self.grid.set_goal(col, row)
        elif mode == "Erase obstacles":
            # Right-click flips draw <-> erase.
            if action == "erase":
                self.grid.paint_obstacle(col, row)
            else:
                self.grid.erase_obstacle(col, row)
        else:
            if action == "draw":
                self.grid.paint_obstacle(col, row)
            else:
                self.grid.erase_obstacle(col, row)
        self.on_map_changed()

    # ---- playback --------------------------------------------------------------

    def step_forward(self) -> None:
        if self.step < self.total():
            self.step += 1
        self._sync_scrub()
        self._update_labels()
        self._repaint()
        if self.trace is not None and self.step == self.total():
            self.timer.Stop()
            self.controls.auto_btn.SetValue(False)   # auto play stops at the end

    def step_back(self) -> None:
        if self.step > 0:
            self.step -= 1
        self._sync_scrub()
        self._update_labels()
        self._repaint()

    def set_step(self, k: int) -> None:
        self.step = max(0, min(int(k), self.total()))
        self._sync_scrub()
        self._update_labels()
        self._repaint()

    def auto_toggled(self, on: bool) -> None:
        if on:
            if self.total() and self.step >= self.total():
                self.set_step(0)     # restart from 0 when already at the end
            self.timer.Start(max(1, 1000 // self.speed), wx.TIMER_CONTINUOUS)
        else:
            self.timer.Stop()

    def on_tick(self, evt) -> None:
        self.step_forward()

    # ---- map operations --------------------------------------------------------

    def set_algo(self, algo: str) -> None:
        self.algo = algo
        self.recompute()

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def set_speed(self, speed: int) -> None:
        self.speed = max(1, int(speed))
        if self.timer.IsRunning():
            self.timer.Start(max(1, 1000 // self.speed), wx.TIMER_CONTINUOUS)

    def set_density(self, density: int) -> None:
        self.density = max(0, min(60, int(density)))

    def random_map(self) -> None:
        self.grid.generate_random(self.rng, self.density)
        self.on_map_changed()

    def clear_map(self) -> None:
        self.grid.clear_map()
        self.on_map_changed()

    def random_start_end(self) -> None:
        tiles = [(c, r) for r in range(self.grid.rows) for c in range(self.grid.cols)
                 if self.grid.passable(c, r)]
        if len(tiles) < 2:
            return
        start = self.rng.choice(tiles)
        goal = self.rng.choice([t for t in tiles if t != start])
        self.grid.set_start(*start)
        self.grid.set_goal(*goal)
        self.on_map_changed()

    def apply_map(self) -> None:
        rows = self.controls.rows_spin.GetValue()
        cols = self.controls.cols_spin.GetValue()
        mode = self.canvas.autosize_mode
        if mode == "Fit tile size":
            self.tile_size = self.canvas.fit_tile(rows, cols, *self.canvas.GetClientSize())
            self.controls.tile_spin.SetValue(self.tile_size)
        elif mode == "Fit map size":
            self.tile_size = self.controls.tile_spin.GetValue()
            cols, rows = self.canvas.fit_dims(self.tile_size, *self.canvas.GetClientSize())
            self.controls.rows_spin.SetValue(rows)
            self.controls.cols_spin.SetValue(cols)
        else:
            self.tile_size = self.controls.tile_spin.GetValue()
        self.build_grid(rows, cols)
        self.canvas.set_map(self.grid, self.trace, 0, self.tile_size)
        self.on_map_changed()

    # ---- keys ------------------------------------------------------------------

    def on_key(self, evt) -> None:
        target = evt.GetEventObject()
        # Text/spin/slider/combo controls own their keys; do not hijack them.
        if isinstance(target, (wx.Control, wx.TextCtrl)):
            evt.Skip()
            return
        key = evt.GetKeyCode()
        if key in (ord(" "), wx.WXK_RIGHT):   # wx.SPACE is absent in this build
            self.step_forward()
        elif key in (wx.WXK_BACK, wx.WXK_LEFT):
            self.step_back()
        elif key in (ord("A"), ord("a")):
            on = not self.controls.auto_btn.GetValue()
            self.controls.auto_btn.SetValue(on)
            self.auto_toggled(on)
        elif key in (ord("R"), ord("r")):
            self.recompute()
        elif key in (ord("G"), ord("g")):
            self.random_map()
        elif key in (ord("C"), ord("c")):
            self.clear_map()
        else:
            evt.Skip()
