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
# Nearby CAD segment search radius (mm). Long store walls beyond this
# must not out-vote the local gondola rectangle.
GEOMETRY_RADIUS_MM = 1400.0
MIN_SEGMENT_LEN_MM = 400.0
MAX_SEGMENT_LEN_MM = 3200.0
BAY_LEN_MIN_MM = 700.0
BAY_LEN_MAX_MM = 2200.0
CARDINAL_SNAP_DEG = 12.0
DIAGONAL_SNAP_DEG = 8.0
RUN_ALIGN_MM = 180.0
RUN_PITCH_MIN_MM = 700.0
RUN_PITCH_MAX_MM = 2600.0


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
        # Prefer bay-sized edges; down-weight long partition walls.
        if BAY_LEN_MIN_MM <= length <= BAY_LEN_MAX_MM:
            weight *= 3.5
        elif length > 4000.0:
            weight *= 0.12
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


def _run_snap(angle: float) -> float:
    snapped, _src = snap_axis_angle(angle)
    # Neighbour consensus is allowed a wider cardinal pull so 292°
    # aisles collapse onto 270/90.
    a = normalize_angle_180(angle)
    wider = [
        (0.0, 28.0),
        (90.0, 28.0),
        (45.0, 12.0),
        (135.0, 12.0),
    ]
    best = (snapped, 999.0)
    for target, tol in wider:
        delta = angle_delta_180(a, target)
        if delta <= tol and delta < best[1]:
            best = (target, delta)
    return best[0]


def smooth_run_orientations(gondolas: List[Dict[str, Any]]) -> int:
    """
    Gondolas on the same aisle (same X or Y, 900-1200 mm pitch) must
    share one unsigned axis. Mixed 0°/270° on a single row is a
    geometry-vote error, not a real store layout.
    """
    n = len(gondolas)
    if n < 2:
        return 0

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        xi = float(gondolas[i].get("x", 0) or 0)
        yi = float(gondolas[i].get("y", 0) or 0)
        for j in range(i + 1, n):
            dx = abs(xi - float(gondolas[j].get("x", 0) or 0))
            dy = abs(yi - float(gondolas[j].get("y", 0) or 0))
            same_row = dy <= RUN_ALIGN_MM and RUN_PITCH_MIN_MM <= dx <= RUN_PITCH_MAX_MM
            same_col = dx <= RUN_ALIGN_MM and RUN_PITCH_MIN_MM <= dy <= RUN_PITCH_MAX_MM
            if same_row or same_col:
                union(i, j)

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    changed = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        votes: Dict[float, int] = {}
        for i in members:
            key = _run_snap(gondolas[i].get("orientation_angle", 0) or 0)
            votes[key] = votes.get(key, 0) + 1
        winner = max(votes, key=votes.get)
        for i in members:
            g = gondolas[i]
            old = float(g.get("orientation_angle", 0) or 0)
            if angle_delta_180(old, winner) < 0.5:
                continue
            dx = float(g.get("pair_dx", 0) or 0)
            dy = float(g.get("pair_dy", 0) or 0)
            placement = directed_from_axis(winner, dx, dy)
            g["orientation_angle"] = round(winner, 3)
            g["placement_angle"] = round(placement, 3)
            g["rotation"] = g["placement_angle"]
            g["orientation"] = classify_orientation(winner)
            src = str(g.get("axis_source", "") or "")
            if "run_consensus" not in src:
                g["axis_source"] = (src + "+run_consensus").strip("+")
            changed += 1
    return changed


def name_key(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def name_tokens(value: Any) -> List[str]:
    return re.findall(r"[A-Z0-9]+", str(value or "").upper())


def score_symbol_candidate(
    code: str,
    family_hint: str,
    type_hint: str,
    family_name: str,
    type_name: str,
) -> int:
    """
    Higher is better. Used to place codes whose TYPE_MAP names do not
    exactly match the Revit family type (6WAY, T2 ARM ONLY, 34RELO).
    """
    code_k = name_key(code)
    hint_k = name_key(type_hint)
    fam_k = name_key(family_name)
    typ_k = name_key(type_name)
    hint_fam = name_key(family_hint)
    score = 0

    if hint_k and typ_k == hint_k:
        score += 120
    if code_k and typ_k == code_k:
        score += 110
    if hint_k and (hint_k in typ_k or typ_k in hint_k):
        score += 70
    if code_k and code_k in typ_k:
        score += 60
    if hint_fam and fam_k == hint_fam:
        score += 40
    elif hint_fam and (hint_fam in fam_k or fam_k in hint_fam):
        score += 20

    code_tokens = set(name_tokens(code))
    hint_tokens = set(name_tokens(type_hint))
    type_tokens = set(name_tokens(type_name))
    ignore = {"THE", "AND", "END", "PANEL", "GONDOLA", "FAMILY"}
    if code_tokens and type_tokens:
        overlap = (code_tokens & type_tokens) - ignore
        score += 8 * len(overlap)
        extra = type_tokens - code_tokens - hint_tokens - ignore
        score -= 6 * len(extra)
        if "T2" in code_tokens and "T2" in type_tokens and "ARM" in type_tokens:
            score += 50
            if "ONLY" in code_tokens and "TABLE" in type_tokens and "ARM" in type_tokens:
                score -= 35
        if "6WAY" in code_k and "6WAY" in typ_k:
            score += 80
        if "6" in code_tokens and "WAY" in type_tokens:
            score += 40
        if "16" in code_tokens and "WAY" in type_tokens:
            score += 40

    return score


def resolve_symbol_name(
    code: str,
    family_hint: str,
    type_hint: str,
    catalog: Sequence[Tuple[str, str]],
    min_score: int = 70,
) -> Optional[Tuple[str, str, int]]:
    """Return (family, type, score) from a Revit-like catalogue."""
    catalog_set = set(catalog)
    if (family_hint, type_hint) in catalog_set:
        return family_hint, type_hint, 1000

    best: Optional[Tuple[str, str, int]] = None
    for family_name, type_name in catalog:
        score = score_symbol_candidate(
            code, family_hint, type_hint, family_name, type_name
        )
        if best is None or score > best[2]:
            best = (family_name, type_name, score)
    if best and best[2] >= min_score:
        return best
    return None


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
