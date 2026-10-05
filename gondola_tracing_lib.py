"""
Shared geometry helpers for gondola DXF tracing and Revit placement.

These functions are used by Gondola_OrientationDetector.py and unit tests.
The Dynamo script duplicates a small subset because Dynamo nodes cannot
reliably import sibling files.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# Typical stacked SIZE/TYPE label gap on a bay (mm).
STACK_PAIR_MAX_MM = 550.0
# Hard cap for pairing (mm). Dense aisles need a tighter cap than 1500.
MAX_PAIR_DIST_MM = 1100.0
PREFERRED_PAIR_DIST_MM = 450.0
# Nearby CAD segment search radius (mm).
GEOMETRY_RADIUS_MM = 2200.0
MIN_SEGMENT_LEN_MM = 350.0
MAX_SEGMENT_LEN_MM = 8000.0
CARDINAL_SNAP_DEG = 8.0
DIAGONAL_SNAP_DEG = 6.0


MTEXT_CODE_RE = re.compile(
    r"\\[A-Za-z][^;\\]*;|[{}]|\\P|\\p|\\~"
)
WHITESPACE_RE = re.compile(r"\s+")


def normalize_code(text: Any) -> str:
    """Uppercase, strip MTEXT formatting, collapse whitespace."""
    if text is None:
        return ""
    raw = str(text)
    raw = raw.replace("\\P", " ").replace("\\p", " ")
    raw = MTEXT_CODE_RE.sub(" ", raw)
    raw = WHITESPACE_RE.sub(" ", raw)
    return raw.upper().strip()


def normalize_angle_360(angle: Any) -> float:
    try:
        angle = float(angle)
    except (TypeError, ValueError):
        return 0.0
    angle %= 360.0
    if angle < 0:
        angle += 360.0
    if abs(angle - 360.0) < 1e-9:
        angle = 0.0
    return angle


def normalize_angle_180(angle: Any) -> float:
    """Unsigned line direction in [0, 180)."""
    angle = normalize_angle_360(angle) % 180.0
    if abs(angle - 180.0) < 1e-9:
        return 0.0
    if abs(angle) < 1e-9:
        return 0.0
    return angle


def angle_delta_180(a: float, b: float) -> float:
    """Smallest difference between two unsigned line directions."""
    d = abs(normalize_angle_180(a) - normalize_angle_180(b)) % 180.0
    return min(d, 180.0 - d)


def angle_delta_360(a: float, b: float) -> float:
    d = abs(normalize_angle_360(a) - normalize_angle_360(b)) % 360.0
    return min(d, 360.0 - d)


def classify_orientation(angle: float) -> str:
    a = normalize_angle_180(angle)
    if a > 90.0:
        a = 180.0 - a
    if a < 25.0:
        return "HORIZONTAL"
    if a > 65.0:
        return "VERTICAL"
    return "DIAGONAL"


def snap_axis_angle(angle: float) -> Tuple[float, str]:
    """
    Snap a tracing axis to the store grid when it is clearly on-grid.

    Retail floor plans are almost always 0/45/90/135. Keep the measured
    value when it is clearly off-grid so true diagonals survive.
    """
    a = normalize_angle_180(angle)
    targets = [
        (0.0, CARDINAL_SNAP_DEG, "snap_0"),
        (90.0, CARDINAL_SNAP_DEG, "snap_90"),
        (45.0, DIAGONAL_SNAP_DEG, "snap_45"),
        (135.0, DIAGONAL_SNAP_DEG, "snap_135"),
    ]
    best = None
    for target, tol, name in targets:
        delta = angle_delta_180(a, target)
        if delta <= tol and (best is None or delta < best[0]):
            best = (delta, target, name)
    if best:
        return best[1], best[2]
    return a, "measured"


def angle_from_offset(dx: float, dy: float) -> float:
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return 0.0
    return normalize_angle_360(math.degrees(math.atan2(dy, dx)))


def unsigned_angle_from_offset(dx: float, dy: float) -> float:
    return normalize_angle_180(angle_from_offset(dx, dy))


def directed_from_axis(axis_180: float, dx: float, dy: float) -> float:
    """
    Lift an unsigned axis into 0-360 using the SIZE -> TYPE vector so
    wall gondolas and end panels keep a consistent facing.
    """
    a1 = normalize_angle_360(axis_180)
    a2 = normalize_angle_360(axis_180 + 180.0)
    pair = angle_from_offset(dx, dy)
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return a1
    if angle_delta_360(pair, a1) <= angle_delta_360(pair, a2):
        return a1
    return a2


def point_segment_distance(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> float:
    vx = x2 - x1
    vy = y2 - y1
    mag2 = vx * vx + vy * vy
    if mag2 < 1e-9:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * vx + (py - y1) * vy) / mag2
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + t * vx), py - (y1 + t * vy))


def insunits_to_mm(insunits: int) -> float:
    """DXF $INSUNITS conversion factor to millimetres."""
    table = {
        0: 1.0,  # unitless — assume already mm for this workflow
        1: 25.4,  # inches
        2: 304.8,  # feet
        4: 1.0,  # millimetres
        5: 10.0,  # centimetres
        6: 1000.0,  # metres
        14: 25.4 / 1000.0,  # mils
        15: 25.4 / 1_000_000.0,
    }
    return table.get(int(insunits or 0), 1.0)


def text_visual_point(
    insert_x: float,
    insert_y: float,
    rotation_deg: float,
    height: float,
    text: str,
    halign: int = 0,
    valign: int = 0,
    width_factor: float = 1.0,
    align_x: Optional[float] = None,
    align_y: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Approximate the visual centre of a TEXT entity.

    DXF insert is an alignment corner, not the glyph centroid. Using the
    corner as the gondola origin systematically shifts placement.
    """
    if align_x is not None and align_y is not None and (halign or valign):
        cx, cy = float(align_x), float(align_y)
    else:
        cx, cy = float(insert_x), float(insert_y)

    if height <= 0:
        return cx, cy

    char_w = max(height * 0.7 * max(width_factor, 0.1), 1.0)
    n = max(len(text or ""), 1)
    width = char_w * n
    ang = math.radians(rotation_deg or 0.0)
    ux, uy = math.cos(ang), math.sin(ang)
    px, py = -uy, ux

    # halign: 0 left, 1 center, 2 right, 3/4 aligned/middle/fit
    if halign in (1, 4):
        along = 0.0
    elif halign in (2,):
        along = -width * 0.5
    else:
        along = width * 0.5

    # valign: 0 baseline, 1 bottom, 2 middle, 3 top
    if valign == 2:
        across = 0.0
    elif valign == 3:
        across = -height * 0.35
    else:
        across = height * 0.35

    return cx + ux * along + px * across, cy + uy * along + py * across


def pair_match_score(
    size_item: Dict[str, Any],
    type_item: Dict[str, Any],
) -> Optional[float]:
    """
    Lower is better. Returns None if the pair is geometrically implausible.
    """
    dx = type_item["x"] - size_item["x"]
    dy = type_item["y"] - size_item["y"]
    dist = math.hypot(dx, dy)
    if dist < 8.0 or dist > MAX_PAIR_DIST_MM:
        return None

    score = dist

    # Prefer typical stacked-label spacing.
    score += abs(dist - PREFERRED_PAIR_DIST_MM) * 0.15

    rot_delta = angle_delta_180(
        size_item.get("label_rotation", size_item.get("rotation", 0.0)),
        type_item.get("label_rotation", type_item.get("rotation", 0.0)),
    )
    if rot_delta > 20.0:
        score += 350.0
    else:
        score += rot_delta * 2.0

    size_layer = str(size_item.get("layer", "") or "")
    type_layer = str(type_item.get("layer", "") or "")
    if size_layer and type_layer and size_layer != type_layer:
        score += 220.0

    # Stacked labels sit on a cardinal axis. Penalise diagonal drift
    # for close pairs (those are almost always stacked, not along-run).
    axis_err = min(abs(dx), abs(dy))
    if dist <= STACK_PAIR_MAX_MM:
        score += axis_err * 0.35
    else:
        # Far pairs should still be aligned with a store axis.
        score += axis_err * 0.15

    return score


def match_size_type_pairs(
    size_texts: Sequence[Dict[str, Any]],
    type_texts: Sequence[Dict[str, Any]],
) -> List[Tuple[int, int, float]]:
    """
    Mutual nearest-neighbour assignment.

    Greedy one-way matching (old script) steals neighbours in dense
    gondola runs and leaves later bays with the wrong TYPE.
    """
    candidates: List[Tuple[float, int, int]] = []
    for si, size_item in enumerate(size_texts):
        for ti, type_item in enumerate(type_texts):
            score = pair_match_score(size_item, type_item)
            if score is None:
                continue
            candidates.append((score, si, ti))

    candidates.sort(key=lambda row: row[0])
    used_s = set()
    used_t = set()
    matches: List[Tuple[int, int, float]] = []
    for score, si, ti in candidates:
        if si in used_s or ti in used_t:
            continue
        used_s.add(si)
        used_t.add(ti)
        size_item = size_texts[si]
        type_item = type_texts[ti]
        dist = math.hypot(
            type_item["x"] - size_item["x"],
            type_item["y"] - size_item["y"],
        )
        matches.append((si, ti, dist))
    return matches


def dominant_segment_angle(
    px: float,
    py: float,
    segments: Sequence[Tuple[float, float, float, float]],
    radius: float = GEOMETRY_RADIUS_MM,
) -> Tuple[Optional[float], float]:
    """
    Weighted vote of nearby CAD stroke directions.

    Returns (angle_180 or None, confidence 0-1).
    """
    bins: Dict[int, float] = {}
    total = 0.0
    for x1, y1, x2, y2 in segments:
        length = math.hypot(x2 - x1, y2 - y1)
        if length < MIN_SEGMENT_LEN_MM or length > MAX_SEGMENT_LEN_MM:
            continue
        dist = point_segment_distance(px, py, x1, y1, x2, y2)
        if dist > radius:
            continue
        ang = unsigned_angle_from_offset(x2 - x1, y2 - y1)
        weight = length / (1.0 + dist)
        # 2° bins covering unsigned [0, 180)
        key = int(round(ang / 2.0)) % 90
        bins[key] = bins.get(key, 0.0) + weight
        total += weight

    if total <= 1e-9:
        return None, 0.0

    best_key = max(bins, key=bins.get)
    confidence = bins[best_key] / total
    angle = normalize_angle_180(best_key * 2.0)
    return angle, min(1.0, confidence)


def estimate_gondola_axis(
    px: float,
    py: float,
    pair_dx: float,
    pair_dy: float,
    pair_dist: float,
    label_rotation: float,
    segments: Sequence[Tuple[float, float, float, float]],
) -> Dict[str, Any]:
    """
    Decide the gondola long-axis.

    SIZE/TYPE labels on a bay are usually stacked across the *width*,
    so the pair vector is perpendicular to the run. Using atan2(pair)
    directly (old script) rotated whole aisles by 90°.
    """
    geom_angle, geom_conf = dominant_segment_angle(px, py, segments)
    pair_angle = unsigned_angle_from_offset(pair_dx, pair_dy)
    pair_perp = normalize_angle_180(pair_angle + 90.0)
    label_axis = normalize_angle_180(label_rotation)

    stacked = 8.0 < pair_dist <= STACK_PAIR_MAX_MM
    along_run = pair_dist > STACK_PAIR_MAX_MM

    if stacked:
        heuristic = pair_perp
        heuristic_source = "pair_perpendicular"
    elif along_run:
        heuristic = pair_angle
        heuristic_source = "pair_parallel"
    else:
        heuristic = label_axis
        heuristic_source = "label_rotation"

    axis = heuristic
    source = heuristic_source

    if geom_angle is not None and geom_conf >= 0.42:
        # Nearby gondola strokes are more reliable than label pairing.
        axis = geom_angle
        source = "cad_geometry"
    elif geom_angle is not None and geom_conf >= 0.28:
        if angle_delta_180(geom_angle, heuristic) <= 18.0:
            axis = geom_angle
            source = "cad_geometry"

    snapped, snap_src = snap_axis_angle(axis)
    placement = directed_from_axis(snapped, pair_dx, pair_dy)

    return {
        "orientation_angle": round(snapped, 3),
        "placement_angle": round(placement, 3),
        "orientation": classify_orientation(snapped),
        "axis_source": source,
        "snap_source": snap_src,
        "geometry_angle": None if geom_angle is None else round(geom_angle, 3),
        "geometry_confidence": round(geom_conf, 3),
        "pair_angle": round(pair_angle, 3),
        "label_rotation": round(normalize_angle_360(label_rotation), 3),
    }


def preferred_json_angle(gondola: Dict[str, Any]) -> Optional[float]:
    """
    Placement must use the traced gondola axis, never the raw DXF
    text rotation (which Dynamo previously consumed first).
    """
    for key in (
        "placement_angle",
        "orientation_angle",
        "geometry_angle",
        "axis_angle",
    ):
        value = gondola.get(key)
        if value is None or value == "":
            continue
        try:
            return normalize_angle_360(float(value))
        except (TypeError, ValueError):
            continue
    return None


def apply_cad_transform(
    x_mm: float,
    y_mm: float,
    origin_x_ft: float,
    origin_y_ft: float,
    basis_xx: float,
    basis_xy: float,
    basis_yx: float,
    basis_yy: float,
    mm_to_ft: float = 1.0 / 304.8,
) -> Tuple[float, float]:
    """Map CAD millimetres through the Revit import transform."""
    x_ft = x_mm * mm_to_ft
    y_ft = y_mm * mm_to_ft
    rx = origin_x_ft + x_ft * basis_xx + y_ft * basis_yx
    ry = origin_y_ft + x_ft * basis_xy + y_ft * basis_yy
    return rx, ry
