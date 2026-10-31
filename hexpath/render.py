"""Pure renderer: a wx.DC (usually a wx.GCDC) + grid + trace + step -> pixels.

Shared by the canvas paint handler and by `main.py --snapshot`, so the window and the
offscreen image are the same code. Pen/brush state belongs to the GCDC, not the
wrapped DC; `DrawPolygon` needs integer points.
"""

import wx

from .grid import Grid
from .hexgrid import center_px, grid_pixel_size, hex_corners
from .trace import Trace

TERRAIN_FILL: dict[int, tuple[int, int, int]] = {
    1: (146, 200, 120),
    2: (96, 158, 90),
    3: (120, 150, 175),
    4: (170, 160, 150),
}
FILL: dict[str, tuple[int, int, int] | None] = {
    "obstacle": (45, 45, 45),
    "frontier_S": (245, 220, 110),
    "visited_S": (120, 190, 235),
    "frontier_G": (240, 150, 200),
    "visited_G": (170, 130, 220),
    "current": (235, 90, 60),
    "path": (215, 120, 255),
    "terrain": None,   # filled from TERRAIN_FILL by grid.cost_at
}
EDGE = (90, 90, 90)
BACKGROUND = (25, 28, 32)
START_MARKER = (60, 200, 90)
GOAL_MARKER = (220, 60, 60)
COST_TEXT = (70, 70, 70)
MARKER_TEXT = (250, 250, 250)
PATH_PEN_COLOR = (220, 40, 40)
PATH_SHADOW = (0, 0, 0)   # drawn first, offset (+1, +1), two pen widths wider

# Terrain cost digits are readable from this radius up; below it the glyph crowds the tile.
DIGIT_MIN_R = 12.0


def _font(size: int) -> wx.Font:
    return wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)


def _centered_text(dc: wx.DC, txt: str, cx: int, cy: int) -> None:
    w, h = dc.GetTextExtent(txt)
    dc.DrawText(txt, cx - w // 2, cy - h // 2)


def render_map(dc: wx.DC, grid: Grid, trace: Trace | None, step: int, tile_size: int,
               ox: int = 0, oy: int = 0) -> None:
    """Paint the whole map for `step` (0 .. trace.total_steps()).

    `ox, oy` place the map's top-left inside the DC; this build's DCs have no
    `Translate`, so the offset is applied to every coordinate.
    """
    R = tile_size / 2.0
    w, h = grid_pixel_size(grid.cols, grid.rows, R)
    dc.SetBackground(wx.Brush(wx.Colour(*BACKGROUND)))
    dc.Clear()

    # Tiles: one pen/brush pair per tile, integer corners.
    edge_pen = wx.Pen(wx.Colour(*EDGE), 1)
    for row in range(grid.rows):
        for col in range(grid.cols):
            tile = (col, row)
            cx, cy = ox + center_px(col, row, R)[0], oy + center_px(col, row, R)[1]
            if trace is not None:
                cls = trace.classify(tile, step, grid)
            else:
                cls = "obstacle" if not grid.passable(col, row) else "terrain"
            fill = TERRAIN_FILL[grid.cost_at(col, row)] if cls == "terrain" else FILL[cls]
            dc.SetBrush(wx.Brush(wx.Colour(*fill)))
            dc.SetPen(edge_pen)
            dc.DrawPolygon(hex_corners(cx, cy, R))
            if cls == "terrain" and R >= DIGIT_MIN_R:
                txt = str(grid.cost_at(col, row))
                dc.SetFont(_font(int(R * 0.7)))
                dc.SetTextForeground(wx.Colour(*COST_TEXT))
                _centered_text(dc, txt, int(round(cx)), int(round(cy)))

    # Path polyline only at the final step, so it never fights the frontier display.
    if trace is not None and trace.found and step == trace.total_steps():
        width = max(4, int(R // 2.5))
        pts = [(int(round(ox + center_px(t[0], t[1], R)[0])),
                int(round(oy + center_px(t[0], t[1], R)[1]))) for t in trace.path]
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.SetPen(wx.Pen(wx.Colour(*PATH_SHADOW), width + 4))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dc.DrawLine(ax + 1, ay + 1, bx + 1, by + 1)
        dc.SetPen(wx.Pen(wx.Colour(*PATH_PEN_COLOR), width))
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            dc.DrawLine(ax, ay, bx, by)

    # Start / goal markers are always visible.
    for tile, colour, letter in ((grid.start, START_MARKER, "S"), (grid.goal, GOAL_MARKER, "E")):
        cx, cy = ox + center_px(tile[0], tile[1], R)[0], oy + center_px(tile[0], tile[1], R)[1]
        ix, iy = int(round(cx)), int(round(cy))
        dc.SetPen(wx.Pen(wx.Colour(*colour), 2))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawCircle(ix, iy, int(round(R * 0.55)))
        dc.SetFont(_font(int(R * 0.6)))
        dc.SetTextForeground(wx.Colour(*MARKER_TEXT))
        _centered_text(dc, letter, ix, iy)
