"""Pointy-top hexagon geometry for odd-row shifted offset grids.

Tile size is the full hex height in pixels; circumradius R = tile_size / 2.
Tiles are addressed as (col, row), row 0 at top, `row & 1` selects the shifted row.
"""

import math

SQRT3 = math.sqrt(3.0)

# Axial neighbor directions, fixed order; the same order is used for every expansion
# so traces are deterministic.
AX_DIRS: list[tuple[int, int]] = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


def offset_to_axial(col: int, row: int) -> tuple[int, int]:
    return (col - (row - (row & 1)) // 2, row)


def axial_to_offset(q: int, r: int) -> tuple[int, int]:
    return (q + (r - (r & 1)) // 2, r)


def neighbors(col: int, row: int, cols: int, rows: int) -> list[tuple[int, int]]:
    """Neighbors in AX_DIRS order, clipped to the grid; edge tiles have degree 2..6."""
    q, r = offset_to_axial(col, row)
    out: list[tuple[int, int]] = []
    for dq, dr in AX_DIRS:
        c, rr = axial_to_offset(q + dq, r + dr)
        if 0 <= c < cols and 0 <= rr < rows:
            out.append((c, rr))
    return out


def hex_distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Cube distance: x = q, z = r, y = -x - z."""
    ax, az = offset_to_axial(*a)
    bx, bz = offset_to_axial(*b)
    ax, az, ay = ax, az, -ax - az
    bx, bz, by = bx, bz, -bx - bz
    return max(abs(ax - bx), abs(ay - by), abs(az - bz))


def center_px(col: int, row: int, R: float) -> tuple[float, float]:
    return (R + SQRT3 * R * (col + 0.5 * (row & 1)), R + 1.5 * R * row)


def hex_corners(cx: float, cy: float, R: float) -> list[tuple[int, int]]:
    """Six integer corner points (screen coords, y down); DrawPolygon needs ints."""
    pts: list[tuple[int, int]] = []
    for i in range(6):
        ang = math.radians(60.0 * i - 30.0)
        pts.append((int(round(cx + R * math.cos(ang))), int(round(cy + R * math.sin(ang)))))
    return pts


def pixel_to_hex(px: float, py: float, R: float) -> tuple[int, int]:
    """Pixel -> (col, row) with cube rounding; the margin R on both axes is baked in."""
    x = (px - R) / R
    y = (py - R) / (1.5 * R)
    q = x / SQRT3 - y / 2
    r = y
    # Cube round: round x, y, z, then fix the coordinate with the largest rounding error.
    x, y, z = q, -q - r, r
    rx, ry, rz = round(x), round(y), round(z)
    dx, dy, dz = abs(rx - x), abs(ry - y), abs(rz - z)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return axial_to_offset(rx, rz)


def grid_pixel_size(cols: int, rows: int, R: float) -> tuple[int, int]:
    return (round(R * (1 + SQRT3 * cols)), round(R * (0.5 + 1.5 * rows)))
