"""Right-hand control panel: map size, random map, edit mode, algorithm, playback,
legend, stats. Every widget calls into the frame through the handler dict `h`.

The frame owns the scrub slider range/value; `scrub_guard` blocks the SetValue ->
EVT_SLIDER feedback loop.
"""

import wx

from .algorithms import COMBO_CHOICES
from .render import FILL, PATH_PEN_COLOR, TERRAIN_FILL

MODE_CHOICES: list[str] = ["Draw obstacles", "Erase obstacles", "Set start", "Set end"]
AUTOSIZE_MODES: list[str] = ["Off", "Fit tile size", "Fit map size"]

# Legend order: terrain costs first, then trace classes.
LEGEND: list[tuple[str, tuple[int, int, int]]] = [
    ("plains 1", TERRAIN_FILL[1]),
    ("forest 2", TERRAIN_FILL[2]),
    ("swamp 3", TERRAIN_FILL[3]),
    ("mountain 4", TERRAIN_FILL[4]),
    ("obstacle", FILL["obstacle"]),
    ("frontier", FILL["frontier_S"]),
    ("visited", FILL["visited_S"]),
    ("current step", FILL["current"]),
    ("path", FILL["path"]),
    ("path line", PATH_PEN_COLOR),
    ("goal-side frontier", FILL["frontier_G"]),
    ("goal-side visited", FILL["visited_G"]),
]


def _paint_swatch(evt) -> None:
    """A legend swatch paints its registered colour.

    With the default background style GTK paints theme grey for these panels in
    this layout, so the colour is drawn directly.
    """
    win = evt.GetEventObject()
    dc = wx.PaintDC(win)
    colour = win.GetBackgroundColour()
    w, h = win.GetClientSize()
    dc.SetPen(wx.Pen(colour))
    dc.SetBrush(wx.Brush(colour))
    dc.DrawRectangle(0, 0, w, h)


def _spin(parent: wx.Window, label: str, lo: int, hi: int, init: int):
    row = wx.BoxSizer(wx.HORIZONTAL)
    row.Add(wx.StaticText(parent, label=label), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
    spin = wx.SpinCtrl(parent, wx.ID_ANY, min=lo, max=hi, initial=init)
    row.Add(spin, 1)
    return row, spin


class ControlPanel(wx.ScrolledWindow):
    def __init__(self, parent, h):
        super().__init__(parent, wx.ID_ANY)
        self.h = h
        self.scrub_guard = False
        self.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                             wx.FONTWEIGHT_NORMAL))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # ---- Map: rows / cols / tile size, applied only by the button. ----
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Map")
        row = wx.BoxSizer(wx.HORIZONTAL)
        r_rows, self.rows_spin = _spin(self, "Rows", 1, 120, 20)
        r_cols, self.cols_spin = _spin(self, "Cols", 1, 120, 26)
        row.Add(r_rows, 1, wx.RIGHT, 6)
        row.Add(r_cols, 1)
        box.Add(row, 0, wx.EXPAND | wx.BOTTOM, 4)
        row = wx.BoxSizer(wx.HORIZONTAL)
        r_tile, self.tile_spin = _spin(self, "Tile size px", 10, 80, 28)
        self.tile_spin.Bind(wx.EVT_SPINCTRL, lambda evt: h["set_tile_size"](evt.GetInt()))
        self.apply_btn = wx.Button(self, wx.ID_ANY, "Apply size")
        self.apply_btn.Bind(wx.EVT_BUTTON, lambda evt: h["apply_map"]())
        row.Add(r_tile, 1, wx.RIGHT, 6)
        row.Add(self.apply_btn, 0)
        box.Add(row, 0, wx.EXPAND)
        self.autosize_box = wx.RadioBox(self, wx.ID_ANY, "Autosize", wx.DefaultPosition,
                                        wx.DefaultSize, AUTOSIZE_MODES, 3, wx.RA_VERTICAL)
        self.autosize_box.SetSelection(1)
        self.autosize_box.Bind(
            wx.EVT_RADIOBOX, lambda evt: h["set_autosize_mode"](self.current_autosize_mode()))
        box.Add(self.autosize_box, 0, wx.EXPAND | wx.TOP, 4)
        sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        # ---- Random map ----------------------------------------------------
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Random map")
        self.density_slider = wx.Slider(self, wx.ID_ANY, 20, 0, 60)
        box.Add(self.density_slider, 0, wx.EXPAND | wx.BOTTOM, 2)
        self.density_label = wx.StaticText(self, label="Obstacle density: 20%")
        box.Add(self.density_label, 0, wx.BOTTOM, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for caption, key in (("Generate random map", "random_map"), ("Clear map", "clear_map")):
            btn = wx.Button(self, wx.ID_ANY, caption)
            btn.Bind(wx.EVT_BUTTON, lambda evt, k=key: h[k]())
            row.Add(btn, 1, wx.RIGHT, 4)
        box.Add(row, 0, wx.EXPAND | wx.BOTTOM, 3)
        self.random_se_btn = wx.Button(self, wx.ID_ANY, "Randomize start/end")
        self.random_se_btn.Bind(wx.EVT_BUTTON, lambda evt: h["random_start_end"]())
        box.Add(self.random_se_btn, 0, wx.EXPAND)
        sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # ---- Edit mode ----------------------------------------------------
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Edit mode")
        self.mode_box = wx.RadioBox(self, wx.ID_ANY, "Edit mode", wx.DefaultPosition,
                                    wx.DefaultSize, MODE_CHOICES, 2, wx.RA_VERTICAL)
        self.mode_box.SetSelection(0)
        self.mode_box.Bind(wx.EVT_RADIOBOX, lambda evt: h["set_mode"](self.current_mode()))
        box.Add(self.mode_box, 0, wx.EXPAND)
        sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # ---- Algorithm ----------------------------------------------------
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Algorithm")
        self.algo_combo = wx.ComboBox(self, wx.ID_ANY, "A*", wx.DefaultPosition,
                                      wx.DefaultSize, COMBO_CHOICES, wx.CB_READONLY)
        self.algo_combo.Bind(wx.EVT_COMBOBOX, lambda evt: h["set_algo"](self.algo_combo.GetValue()))
        box.Add(self.algo_combo, 0, wx.EXPAND | wx.BOTTOM, 4)
        self.auto_run_check = wx.CheckBox(self, wx.ID_ANY, "Auto-run on map change")
        self.auto_run_check.SetValue(True)
        box.Add(self.auto_run_check, 0, wx.BOTTOM, 4)
        self.run_btn = wx.Button(self, wx.ID_ANY, "Run")
        self.run_btn.Bind(wx.EVT_BUTTON, lambda evt: h["run"]())
        box.Add(self.run_btn, 0, wx.EXPAND)
        sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # ---- Playback ----------------------------------------------------
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Playback")
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.back_btn = wx.Button(self, wx.ID_ANY, "← Back")
        self.forward_btn = wx.Button(self, wx.ID_ANY, "Forward")
        self.auto_btn = wx.ToggleButton(self, wx.ID_ANY, "Auto")
        row.Add(self.back_btn, 1, wx.RIGHT, 4)
        row.Add(self.forward_btn, 1, wx.RIGHT, 4)
        row.Add(self.auto_btn, 1)
        box.Add(row, 0, wx.EXPAND | wx.BOTTOM, 4)
        self.back_btn.Bind(wx.EVT_BUTTON, lambda evt: h["step_back"]())
        self.forward_btn.Bind(wx.EVT_BUTTON, lambda evt: h["step_forward"]())
        self.auto_btn.Bind(wx.EVT_TOGGLEBUTTON, lambda evt: h["auto_toggled"](evt.IsChecked()))

        self.speed_slider = wx.Slider(self, wx.ID_ANY, 10, 1, 30)
        box.Add(self.speed_slider, 0, wx.EXPAND | wx.BOTTOM, 2)
        self.speed_label = wx.StaticText(self, label="Speed: 10 steps/sec")
        box.Add(self.speed_label, 0, wx.BOTTOM, 4)
        self.scrub_slider = wx.Slider(self, wx.ID_ANY, 0, 0, 0)
        box.Add(self.scrub_slider, 0, wx.EXPAND | wx.BOTTOM, 2)
        self.step_label = wx.StaticText(self, label="Step 0 / 0")
        box.Add(self.step_label, 0)
        sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # ---- Legend -------------------------------------------------------
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Legend")
        half = (len(LEGEND) + 1) // 2
        columns = wx.BoxSizer(wx.HORIZONTAL)
        for start in (0, half):
            col = wx.BoxSizer(wx.VERTICAL)
            for label, color in LEGEND[start:start + half]:
                row = wx.BoxSizer(wx.HORIZONTAL)
                swatch = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(18, 18))
                swatch.SetBackgroundColour(wx.Colour(*color))
                swatch.SetBackgroundStyle(wx.BG_STYLE_PAINT)
                swatch.Bind(wx.EVT_PAINT, _paint_swatch)
                row.Add(swatch, 0, wx.RIGHT, 6)
                row.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
                col.Add(row, 0, wx.EXPAND | wx.BOTTOM, 2)
            columns.Add(col, 0, wx.RIGHT, 6)
        box.Add(columns, 0, wx.EXPAND)
        sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # ---- Stats --------------------------------------------------------
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Stats")
        self.stats_label = wx.StaticText(self, label="Path found: no")
        box.Add(self.stats_label, 0, wx.EXPAND)
        sizer.Add(box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self.SetSizer(sizer)
        self.SetAutoLayout(True)
        # The control content is taller than the pane (~820 px), so the panel scrolls:
        # without a virtual size the sizer collapses the legend rows to zero height.
        cw, ch = sizer.GetMinSize()
        vw, vh = max(cw, 380), ch
        self.SetVirtualSize((vw, vh))
        self.SetScrollbars(1, 1, vw, vh)

        # Spin controls and sliders are bound after every widget exists.
        self._bind_sliders(h)

    def _bind_sliders(self, h):
        self.density_slider.Bind(wx.EVT_SLIDER, self._on_density)
        self.speed_slider.Bind(wx.EVT_SLIDER, self._on_speed)
        self.scrub_slider.Bind(wx.EVT_SLIDER, self._on_scrub)

    def current_mode(self) -> str:
        """The label the frame reads for the current edit mode."""
        return self.mode_box.GetString(self.mode_box.GetSelection())

    def current_autosize_mode(self) -> str:
        """The label the frame reads for the current autosize mode."""
        return self.autosize_box.GetString(self.autosize_box.GetSelection())

    def set_step_labels(self, step: int, total: int) -> None:
        self.step_label.SetLabel(f"Step {step} / {total}")

    def _on_density(self, evt):
        value = self.density_slider.GetValue()
        self.density_label.SetLabel(f"Obstacle density: {value}%")
        self.h["set_density"](value)

    def _on_speed(self, evt):
        value = self.speed_slider.GetValue()
        self.speed_label.SetLabel(f"Speed: {value} steps/sec")
        self.h["set_speed"](value)

    def _on_scrub(self, evt):
        if self.scrub_guard:
            return          # programmatic SetValue from the frame
        self.h["scrub"](self.scrub_slider.GetValue())
