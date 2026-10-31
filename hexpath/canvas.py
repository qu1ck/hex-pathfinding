"""Scrollable hex map canvas: paint via GCDC, mouse edits as (col, row, action).

The canvas is mode-agnostic: left button emits "draw", right button emits "erase",
and the frame maps that pair plus the current edit mode to the actual grid operation.
"""

import wx

from .hexgrid import SQRT3, grid_pixel_size, pixel_to_hex
from .render import render_map


class HexCanvas(wx.ScrolledWindow):
    def __init__(self, parent, on_tile_event, on_fit, on_fit_grid):
        super().__init__(parent)
        self.on_tile_event = on_tile_event
        self.on_fit = on_fit
        self.on_fit_grid = on_fit_grid
        self.grid = None
        self.trace = None
        self.step = 0
        self.tile_size = 28
        self.map_size = (0, 0)
        self.offset = (0, 0)   # top-left of the painted map inside the pane
        self.autosize_mode = "Fit tile size"   # "Off" | "Fit tile size" | "Fit map size"
        self.dragging = False
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)   # must be set before binding paint
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_up)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.SetFocus()

    def fit_tile(self, cols: int, rows: int, w: int, h: int) -> int:
        """Largest tile size whose whole map fits the `w` x `h` area (floor, so no overflow)."""
        if w < 2 or h < 2:
            return self.tile_size
        r = min(w / (1 + SQRT3 * cols), h / (0.5 + 1.5 * rows))
        return max(4, min(80, int(2 * r)))

    def fit_dims(self, tile_size: int, w: int, h: int) -> tuple[int, int]:
        """Cols/rows that fill the `w` x `h` pane at a fixed tile size (floor, so no overflow)."""
        if w < 2 or h < 2:
            return (self.grid.cols, self.grid.rows) if self.grid else (1, 1)
        R = tile_size / 2.0
        cols = max(1, min(120, int((w / R - 1) / SQRT3)))
        rows = max(1, min(120, int((h / R - 0.5) / 1.5)))
        return cols, rows

    def _recompute_offset(self) -> None:
        """Center the map in the pane; offsets feed both paint and mouse mapping."""
        if self.grid is None:
            return
        cw, ch = self.GetClientSize()
        w, h = self.map_size
        self.offset = (max(0, (cw - w) // 2), max(0, (ch - h) // 2))

    def on_size(self, evt):
        evt.Skip()
        self._recompute_offset()
        self.Refresh()
        if self.grid is None:
            return
        cw, ch = self.GetClientSize()
        if self.autosize_mode == "Fit tile size":
            tile = self.fit_tile(self.grid.cols, self.grid.rows, cw, ch)
            if tile != self.tile_size:
                self.on_fit(tile)
        elif self.autosize_mode == "Fit map size":
            cols, rows = self.fit_dims(self.tile_size, cw, ch)
            if (cols, rows) != (self.grid.cols, self.grid.rows):
                self.on_fit_grid(cols, rows)

    def set_map(self, grid, trace, step, tile_size):
        """Store the view, resize the virtual area to the map, repaint."""
        self.grid = grid
        self.trace = trace
        self.step = step
        self.tile_size = tile_size
        w, h = grid_pixel_size(grid.cols, grid.rows, tile_size / 2.0)
        self.map_size = (w, h)
        cw, ch = self.GetClientSize()
        vw, vh = max(w, cw), max(h, ch)
        self.SetVirtualSize((vw, vh))
        self.SetScrollbars(1, 1, vw, vh)
        self._recompute_offset()
        self.Refresh()
        self.Update()

    def on_paint(self, evt):
        dc = wx.BufferedPaintDC(self)
        self.PrepareDC(dc)
        g = wx.GCDC(dc)
        if self.grid is not None:
            render_map(g, self.grid, self.trace, self.step, self.tile_size,
                       self.offset[0], self.offset[1])

    # Mouse: the window scrolls, so raw event coords are not map coords.
    def _tile_at(self, evt):
        if self.grid is None:
            return None
        vx, vy = self.CalcUnscrolledPosition(int(evt.GetX()), int(evt.GetY()))
        col, row = pixel_to_hex(vx - self.offset[0], vy - self.offset[1], self.tile_size / 2.0)
        if not self.grid.in_bounds(col, row):
            return None
        return col, row

    def _act(self, evt, action):
        tile = self._tile_at(evt)
        if tile is None:
            return
        self.on_tile_event(tile[0], tile[1], action)

    def on_left_down(self, evt):
        self.SetFocus()
        self.dragging = True
        self._act(evt, "draw")

    def on_motion(self, evt):
        if self.dragging and evt.Dragging():
            self._act(evt, "draw")

    def on_left_up(self, evt):
        self.dragging = False

    def on_right_down(self, evt):
        self._act(evt, "erase")
