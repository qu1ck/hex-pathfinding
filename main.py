"""Hex Pathfinding Visualizer — entry point.

Headless verification paths:
  --snapshot PATH  renders only the canvas content offscreen (no window).
  --capture  PATH  shows the real frame, grabs the whole client area.
"""

import argparse
import random
import sys

import wx

from hexpath.algorithms import ALGORITHMS
from hexpath.grid import Grid
from hexpath.hexgrid import grid_pixel_size
from hexpath.render import render_map


def build_map(rows: int, cols: int, seed: int, density: int, algo: str):
    grid = Grid(rows, cols)
    grid.generate_random(random.Random(seed), density)
    trace = ALGORITHMS[algo](grid)
    return grid, trace


def resolve_step(step: int | None, total: int) -> int:
    if step is None:
        return total
    return max(0, min(step, total))


def do_snapshot(path: str, rows: int, cols: int, tile: int, seed: int, density: int,
               algo: str, step: int | None) -> bool:
    grid, trace = build_map(rows, cols, seed, density, algo)
    step = resolve_step(step, trace.total_steps())
    w, h = grid_pixel_size(cols, rows, tile / 2.0)
    bmp = wx.Bitmap((w, h))
    dc = wx.MemoryDC(bmp)
    g = wx.GCDC(dc)
    render_map(g, grid, trace, step, tile)
    dc.SelectObject(wx.NullBitmap)
    return bmp.ConvertToImage().SaveFile(path, wx.BITMAP_TYPE_PNG)


def grab_client_area(frame: wx.Frame, path: str) -> bool:
    pos = frame.ClientToScreen((0, 0))
    w, h = frame.GetClientSize()
    sdc = wx.ScreenDC()
    bmp = wx.Bitmap((w, h))
    mdc = wx.MemoryDC(bmp)
    mdc.Blit(0, 0, w, h, sdc, pos[0], pos[1])
    mdc.SelectObject(wx.NullBitmap)
    return bmp.ConvertToImage().SaveFile(path, wx.BITMAP_TYPE_PNG)


def finish_capture(frame: wx.Frame, path: str, result: list[bool]) -> None:
    result.append(grab_client_area(frame, path))
    frame.Close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="main.py", description=__doc__)
    p.add_argument("--rows", type=int, default=20)
    p.add_argument("--cols", type=int, default=26)
    p.add_argument("--tile", type=int, default=28)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--density", type=int, default=20)
    p.add_argument("--algo", type=str, default="A*", choices=list(ALGORITHMS))
    p.add_argument("--step", type=int, default=None)
    p.add_argument("--snapshot", type=str, default=None)
    p.add_argument("--capture", type=str, default=None)
    p.add_argument("--exit-after", type=int, default=None, dest="exit_after")
    return p.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not 1 <= args.rows <= 120 or not 1 <= args.cols <= 120:
        print("rows and cols must be within 1..120", file=sys.stderr)
        return 2
    if not 10 <= args.tile <= 80:
        print("tile must be within 10..80", file=sys.stderr)
        return 2

    if args.snapshot:
        app = wx.App(False)
        ok = do_snapshot(args.snapshot, args.rows, args.cols, args.tile, args.seed,
                         args.density, args.algo, args.step)
        del app
        return 0 if ok else 1

    if args.capture:
        from hexpath.frame import MainFrame

        app = wx.App(False)
        frame = MainFrame(args.rows, args.cols, args.tile, args.seed, args.density, args.algo)
        frame.Show()
        if args.step is not None:
            frame.set_step(args.step)
        result: list[bool] = []
        if args.exit_after is not None:
            wx.CallLater(args.exit_after, lambda: finish_capture(frame, args.capture, result))
            app.MainLoop()
            return 0 if result and result[0] else 1
        wx.Yield()
        wx.SafeYield()
        finish_capture(frame, args.capture, result)
        return 0 if result and result[0] else 1

    from hexpath.frame import MainFrame

    app = wx.App(True)
    frame = MainFrame(args.rows, args.cols, args.tile, args.seed, args.density, args.algo)
    frame.Show()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
