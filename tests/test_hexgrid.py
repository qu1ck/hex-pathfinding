"""Hex geometry: offset<->axial, pixel round-trip, corners, neighbors, distances, canvas fit."""

from hexpath.hexgrid import (
    AX_DIRS,
    axial_to_offset,
    center_px,
    grid_pixel_size,
    hex_corners,
    hex_distance,
    neighbors,
    offset_to_axial,
    pixel_to_hex,
)

COLS, ROWS = 26, 20


def test_offset_axial_round_trip():
    """Every cell of a 9x9 grid maps to axial and back with 0 mismatches."""
    for row in range(9):
        for col in range(9):
            q, r = offset_to_axial(col, row)
            assert axial_to_offset(q, r) == (col, row)


def test_center_px_round_trip():
    """pixel_to_hex(center_px(col, row, R)) == (col, row) for R = 7.0 and 14.0."""
    for R in (7.0, 14.0):
        for row in range(ROWS):
            for col in range(COLS):
                cx, cy = center_px(col, row, R)
                assert pixel_to_hex(cx, cy, R) == (col, row), (col, row, R)


def test_hex_corners_are_integer_and_have_top_vertex():
    """6 integer corner points, with the top vertex (cx, cy - R) present."""
    for R in (7.0, 14.0, 20.0):
        for row in range(ROWS):
            for col in range(COLS):
                cx, cy = center_px(col, row, R)
                pts = hex_corners(cx, cy, R)
                assert len(pts) == 6
                assert all(isinstance(x, int) and isinstance(y, int) for x, y in pts), pts
                assert (int(round(cx)), int(round(cy - R))) in pts


def test_neighbor_symmetry():
    """b in neighbors(a) => a in neighbors(b) for every cell of the 26x20 grid."""
    for row in range(ROWS):
        for col in range(COLS):
            for n in neighbors(col, row, COLS, ROWS):
                assert (col, row) in neighbors(n[0], n[1], COLS, ROWS), ((col, row), n)


def test_neighbor_degrees_and_directions():
    """Edge cells have degree 2..5, interior cells 6; neighbors are AX_DIRS clipped."""
    degrees = {len(neighbors(col, row, COLS, ROWS))
               for row in range(ROWS) for col in range(COLS)}
    assert degrees == {2, 3, 4, 5, 6}
    assert neighbors(0, 0, COLS, ROWS) == [(1, 0), (0, 1)]          # top-left corner, degree 2
    interior = neighbors(12, 10, COLS, ROWS)
    assert len(interior) == 6
    q, r = offset_to_axial(12, 10)
    expected = [axial_to_offset(q + dq, r + dr) for dq, dr in AX_DIRS]
    assert interior == [n for n in expected if 0 <= n[0] < COLS and 0 <= n[1] < ROWS]


def test_hex_distance_values():
    """0 for identical tiles, 1 for each of the 6 neighbors, 2 for (0,0)->(0,2), 8 for (0,0)->(5,5)."""
    assert hex_distance((0, 0), (0, 0)) == 0
    for n in neighbors(12, 10, COLS, ROWS):
        assert hex_distance((12, 10), n) == 1
    assert hex_distance((0, 0), (0, 2)) == 2
    assert hex_distance((0, 0), (5, 5)) == 8


def test_grid_pixel_size_exact():
    assert grid_pixel_size(26, 20, 14) == (644, 427)


def test_canvas_fits_every_hex_corner():
    """Every corner point lies in [0, w] x [0, h]; the extents measure 2..644 and 0..427.

    Corners extend R*sqrt(3)/2 horizontally from the center, so the fit is asserted on
    corner extents, not on center + R.
    """
    w, h = grid_pixel_size(COLS, ROWS, 14)
    xs, ys = [], []
    for row in range(ROWS):
        for col in range(COLS):
            cx, cy = center_px(col, row, 14.0)
            for x, y in hex_corners(cx, cy, 14.0):
                xs.append(x)
                ys.append(y)
    assert min(xs) == 2
    assert max(xs) == 644 == w
    assert min(ys) == 0
    assert max(ys) == 427 == h
    assert all(0 <= x <= w for x in xs)
    assert all(0 <= y <= h for y in ys)
