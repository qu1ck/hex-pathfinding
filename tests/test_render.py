"""Renderer pixels: obstacle/terrain fills, the current tile, background margins.

One MemoryDC + one GCDC per scene; the bitmap is released from the DC only to convert
it to an image. `FindPoint`/`GetXY` do not exist in this build, so sampling uses
`GetRed/GetGreen/GetBlue`. Samples sit on the fill area (off the marker ring, the
'S'/'E' glyph and the terrain digit) with a ±3 per-channel tolerance for GCDC
antialiasing.
"""

import random

import pytest
import wx

from hexpath.algorithms import astar
from hexpath.grid import Grid
from hexpath.hexgrid import center_px, grid_pixel_size
from hexpath.render import BACKGROUND, FILL, PATH_PEN_COLOR, TERRAIN_FILL, render_map

TILE = 24
R = TILE / 2.0
TOL = 3


@pytest.fixture(scope="module")
def app():
    return wx.App(False)


@pytest.fixture
def scene(app):
    grid = Grid(3, 3)
    grid.generate_random(random.Random(5), 20)
    trace = astar(grid)
    w, h = grid_pixel_size(grid.cols, grid.rows, R)
    bmp = wx.Bitmap((w, h))
    dc = wx.MemoryDC(bmp)
    g = wx.GCDC(dc)
    yield grid, trace, bmp, dc, g
    dc.SelectObject(wx.NullBitmap)


def render_step(dc, g, bmp, grid, trace, step):
    """Paint `step` and hand back the resulting image."""
    render_map(g, grid, trace, step, TILE)
    dc.SelectObject(wx.NullBitmap)
    img = bmp.ConvertToImage()
    dc.SelectObject(bmp)
    return img


def px(img, x, y):
    xi, yi = int(round(x)), int(round(y))
    return (img.GetRed(xi, yi), img.GetGreen(xi, yi), img.GetBlue(xi, yi))


def fill_point(tile):
    """A point inside the tile fill, clear of the marker ring stroke (radius 0.55R,
    pen width 2), the 'S'/'E' glyph and the terrain digit, all of which sit on the
    tile center. 0.75R is inside the hex (inradius 0.87R) and outside the ring.
    """
    cx, cy = center_px(tile[0], tile[1], R)
    return cx + 0.75 * R, cy


def near(color, expected, tol=TOL):
    return all(abs(a - b) <= tol for a, b in zip(color, expected))


def test_obstacle_center_is_obstacle_fill(scene):
    grid, trace, bmp, dc, g = scene
    obstacles = [(c, r) for r in range(grid.rows) for c in range(grid.cols)
                 if grid.cost_at(c, r) == 0]
    assert obstacles, "seeded 3x3 map must contain an obstacle"
    img = render_step(dc, g, bmp, grid, trace, 0)
    for tile in obstacles:
        cx, cy = center_px(tile[0], tile[1], R)
        assert near(px(img, cx, cy), FILL["obstacle"]), tile


def test_passable_tile_shows_terrain_fill(scene):
    grid, trace, bmp, dc, g = scene
    tiles = [(c, r) for r in range(grid.rows) for c in range(grid.cols)
             if grid.passable(c, r) and (c, r) not in (grid.start, grid.goal)]
    assert tiles
    img = render_step(dc, g, bmp, grid, trace, 0)
    for tile in tiles:
        assert near(px(img, *fill_point(tile)), TERRAIN_FILL[grid.cost_at(*tile)]), tile


def test_first_expansion_is_current(scene):
    grid, trace, bmp, dc, g = scene
    img = render_step(dc, g, bmp, grid, trace, 1)
    assert near(px(img, *fill_point(trace.steps[0])), FILL["current"])


def test_margin_is_background(scene):
    grid, trace, bmp, dc, g = scene
    img = render_step(dc, g, bmp, grid, trace, 0)
    assert near(px(img, 0, 0), BACKGROUND)


def test_path_line_is_red_with_black_shadow(scene):
    """The final-step polyline is red with a black shadow layer under it.

    The shadow is drawn first, offset (+1, +1) and one pen width wider, so the
    anti-aliased fringe beside the red stroke is the black layer blended with red:
    every channel sits at the same fraction of the pen color, below full strength.
    """
    grid, trace, bmp, dc, g = scene
    img = render_step(dc, g, bmp, grid, trace, trace.total_steps())
    width = max(2, int(R // 4))
    (ax, ay) = center_px(*trace.path[0], R)
    (bx, by) = center_px(*trace.path[1], R)
    mx, my = (ax + bx) / 2, (ay + by) / 2
    assert near(px(img, mx, my), PATH_PEN_COLOR, 6), (mx, my)
    shadow = px(img, mx, my + width // 2 + 2)
    k = shadow[0] / PATH_PEN_COLOR[0]
    assert 0.0 <= k < 0.9, (shadow, k)
    assert all(abs(shadow[i] - k * PATH_PEN_COLOR[i]) <= 12 for i in range(3)), shadow
