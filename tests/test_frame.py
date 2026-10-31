"""MainFrame behavior: edit-mode mapping, playback, auto-stop, labels.

Runs under xvfb (needs a display for the frame).
"""

import pytest
import wx

from hexpath.frame import MainFrame
from hexpath.hexgrid import center_px, grid_pixel_size


class _Click:
    """Mouse-event stand-in: the canvas reads only GetX/GetY."""

    def __init__(self, x, y):
        self._x, self._y = int(x), int(y)

    def GetX(self):
        return self._x

    def GetY(self):
        return self._y


@pytest.fixture(scope="module")
def app():
    return wx.App(False)


@pytest.fixture
def frame(app):
    f = MainFrame(rows=6, cols=8, tile_size=20, seed=3, density=0, algo="A*")
    yield f
    f.Destroy()


def test_draw_paints_obstacle_and_recomputes(frame):
    frame.set_mode("Draw obstacles")
    frame.apply_tile_event(2, 1, "draw")
    assert frame.grid.cost_at(2, 1) == 0
    # "Auto-run on map change" is checked by default, so the trace is recomputed.
    assert frame.step == 0


def test_right_click_erases(frame):
    frame.apply_tile_event(2, 1, "erase")
    assert frame.grid.cost_at(2, 1) == 1


def test_set_start_and_set_end(frame):
    frame.apply_tile_event(3, 2, "set_start")
    assert frame.grid.start == (3, 2)
    frame.set_mode("Set end")
    frame.apply_tile_event(3, 2, "draw")
    assert frame.grid.goal == (3, 2)


def test_radio_box_labels_are_readable_for_every_mode(frame):
    """Regression: wxPython 4.2.3 `RadioBox.GetLabel(index)` raises
    `TypeError: Control.GetLabel(): too many arguments`, which crashed every
    edit-mode switch. Item labels come from `GetString(index)`.
    """
    box = frame.controls.mode_box
    labels = ["Draw obstacles", "Erase obstacles", "Set start", "Set end"]
    for index, label in enumerate(labels):
        box.SetSelection(index)
        assert frame.controls.current_mode() == label, index
    # The value the panel hands to the frame must drive the grid operation.
    box.SetSelection(2)
    frame.set_mode(frame.controls.current_mode())
    frame.apply_tile_event(1, 1, "draw")
    assert frame.grid.start == (1, 1) and frame.grid.cost_at(1, 1) == 1
    box.SetSelection(3)
    frame.set_mode(frame.controls.current_mode())
    frame.apply_tile_event(4, 2, "draw")
    assert frame.grid.goal == (4, 2)
    box.SetSelection(0)
    frame.set_mode(frame.controls.current_mode())
    frame.apply_tile_event(2, 0, "draw")
    assert frame.grid.cost_at(2, 0) == 0


def test_forward_back_and_auto_stop(frame):
    frame.step_forward()
    frame.step_forward()
    assert frame.step == 2
    frame.step_back()
    assert frame.step == 1
    total = frame.trace.total_steps()
    while frame.step < total:
        frame.step_forward()
    assert frame.step == total
    assert frame.timer.IsRunning() is False
    assert frame.controls.auto_btn.GetValue() is False


def test_auto_toggles_timer(frame):
    frame.set_step(0)
    frame.set_speed(20)
    frame.auto_toggled(True)
    assert frame.timer.IsRunning() is True
    frame.auto_toggled(False)
    assert frame.timer.IsRunning() is False


def test_stats_and_scrub_range(frame):
    frame.recompute()
    assert "Path found: yes" in frame.controls.stats_label.GetLabel()
    assert frame.controls.scrub_slider.GetMax() == frame.trace.total_steps()
    assert frame.controls.scrub_slider.GetValue() == 0
    assert frame.controls.step_label.GetLabel() == f"Step 0 / {frame.trace.total_steps()}"


def test_resize_autosizes_the_map(frame):
    """The canvas refits the tile size to its pane on every resize; selecting "Off"
    freezes it. The map must never clip or force scrolling, and the tile-size spin
    must follow the fitted value.
    """
    wx.Yield()
    wx.SafeYield()
    base = frame.tile_size
    cw, ch = frame.canvas.GetClientSize()
    w, h = grid_pixel_size(frame.grid.cols, frame.grid.rows, base / 2.0)
    assert w <= cw and h <= ch, (base, (w, h), (cw, ch))
    assert frame.canvas.GetScrollRange(wx.VERTICAL) == 1
    frame.SetSize((700, 400))
    wx.Yield()
    wx.SafeYield()
    small = frame.tile_size
    assert small < base
    w, h = grid_pixel_size(frame.grid.cols, frame.grid.rows, small / 2.0)
    cw, ch = frame.canvas.GetClientSize()
    assert w <= cw and h <= ch, (small, (w, h), (cw, ch))
    assert frame.controls.tile_spin.GetValue() == small
    frame.SetSize((1200, 820))
    wx.Yield()
    wx.SafeYield()
    assert frame.tile_size > small
    cw, ch = frame.canvas.GetClientSize()
    w, h = grid_pixel_size(frame.grid.cols, frame.grid.rows, frame.tile_size / 2.0)
    ox, oy = frame.canvas.offset
    assert (ox, oy) == (max(0, (cw - w) // 2), max(0, (ch - h) // 2)), (ox, oy, (cw, ch), (w, h))
    # Clicks map through the same offset as the paint.
    cx, cy = center_px(2, 1, frame.tile_size / 2.0)
    assert frame.canvas._tile_at(_Click(ox + int(round(cx)), oy + int(round(cy)))) == (2, 1)
    frame.set_autosize_mode("Off")
    fixed = frame.tile_size
    frame.SetSize((900, 500))
    wx.Yield()
    wx.SafeYield()
    assert frame.tile_size == fixed
    # A rebuilt grid refits through apply_map as well.
    frame.set_autosize_mode("Fit tile size")
    frame.controls.rows_spin.SetValue(4)
    frame.controls.cols_spin.SetValue(5)
    frame.apply_map()
    wx.Yield()
    w, h = grid_pixel_size(5, 4, frame.tile_size / 2.0)
    cw, ch = frame.canvas.GetClientSize()
    assert frame.tile_size == 80 and w <= cw and h <= ch


def test_map_size_autosize_mode(frame):
    """"Fit map size" keeps the tile size and rebuilds the grid to fill the pane;
    "Off" freezes dimensions and tile size. Selection runs through the real
    `EVT_RADIOBOX` handler, so the panel->frame path is exercised.
    """
    box = frame.controls.autosize_box
    for i, label in enumerate(["Off", "Fit tile size", "Fit map size"]):
        box.SetSelection(i)
        assert frame.controls.current_autosize_mode() == label, i
    frame.controls.tile_spin.SetValue(20)
    box.SetSelection(2)
    wx.PostEvent(box, wx.CommandEvent(wx.wxEVT_RADIOBOX, box.GetId()))
    wx.Yield()
    wx.SafeYield()
    cw, ch = frame.canvas.GetClientSize()
    cols, rows = frame.canvas.fit_dims(20, cw, ch)
    assert (frame.grid.cols, frame.grid.rows) == (cols, rows), (cols, rows, cw, ch)
    assert frame.tile_size == 20
    assert frame.controls.cols_spin.GetValue() == cols
    assert frame.controls.rows_spin.GetValue() == rows
    assert frame.grid.start == (0, 0) and frame.grid.goal == (cols - 1, rows - 1)
    w, h = grid_pixel_size(cols, rows, 10.0)
    assert w <= cw and h <= ch
    assert frame.canvas.GetScrollRange(wx.VERTICAL) == 1
    frame.SetSize((900, 500))
    wx.Yield()
    wx.SafeYield()
    cw2, ch2 = frame.canvas.GetClientSize()
    cols2, rows2 = frame.canvas.fit_dims(20, cw2, ch2)
    assert (frame.grid.cols, frame.grid.rows) == (cols2, rows2), (cols2, rows2, cw2, ch2)
    assert cols2 < cols and rows2 < rows
    assert frame.tile_size == 20
    box.SetSelection(0)
    wx.PostEvent(box, wx.CommandEvent(wx.wxEVT_RADIOBOX, box.GetId()))
    wx.Yield()
    wx.SafeYield()
    frame.SetSize((1200, 820))
    wx.Yield()
    wx.SafeYield()
    assert (frame.grid.cols, frame.grid.rows) == (cols2, rows2)
    assert frame.tile_size == 20
