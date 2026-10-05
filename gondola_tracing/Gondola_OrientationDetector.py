# Gondola_OrientationDetector.py
#
# Original File1 collector (the run that filled most bays).
# Version 2026-10-05t-drawn-shape
#
# Collect is unchanged: leftover named blocks + modelspace TEXT.
# Position and orientation are corrected after collect:
#   SIZE+TYPE paired mutual-nearest, family XY = bay centre, then
#   each bay is read from the gondola drawn in the CAD - nested
#   blocks exploded, runs drawn as one outline handled, and the
#   block INSERT used when labels and outlines are in different
#   spaces. Neighbour-run voting only fills in what is left.
#
# Purpose:
#   1. Read gondola labels from a DXF file.
#   2. Detect complete gondola codes.
#   3. Detect SIZE + TYPE combinations.
#   4. Determine the physical tracing direction.
#   5. Store the actual tracing angle as "orientation_angle".
#   6. Export the gondola data to JSON for Dynamo/Revit placement.
#
# Important:
#   orientation_angle is the actual DXF tracing direction:
#
#       0°   = +X direction
#       90°  = +Y direction
#       45°  = diagonal
#
#   The Dynamo placement script can then convert this physical
#   tracing angle into the required Revit family rotation.


# ============================================================
# PLATFORM PATCH
# ============================================================

import platform as _platform

if not hasattr(_platform, "_patched"):

    _orig = _platform._syscmd_ver

    def _safe_syscmd_ver(*a, **kw):
        try:
            return _orig(*a, **kw)
        except Exception:
            return ("", "", "", "")

    _platform._syscmd_ver = _safe_syscmd_ver
    _platform._patched = True


# ============================================================
# IMPORTS
# ============================================================

import ezdxf
import json
import sys
import math


try:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )
except Exception:
    pass


# ============================================================
# FILE PATHS
# ============================================================

DXF_FILE_PATH = r"C:\Users\msharan\OneDrive - Kmart Australia Limited\Desktop\Stores Foundry\PPT , Requirements, Demo videos, Pics\1131 Marrickville-Existing plan trace exercise_2 - Floor Plan - 1-0 EXISTING CONDITIONS - GROUND.dxf"

OUTPUT_JSON = r"C:\Users\msharan\OneDrive - Kmart Australia Limited\Desktop\Stores Foundry\Tracing\json\gondola_data_Marrickville_New4.json"
SCRIPT_VERSION = "2026-10-05t-drawn-shape"


# ============================================================
# SIZE CODES
# ============================================================

SIZE_CODES = {
    "15F",
    "21F",
    "34F",
    "34H",
    "34S",
    "36W",
    "36B",
    "18F",
    "12W",
    "15W",
    "27H",
    "28F",
    "42F",
    "21H"
}


# ============================================================
# TYPE CODES
# ============================================================

TYPE_CODES = {
    "MCA",
    "MCS",
    "LCA",
    "LCS",
    "MOA",
    "MOS",
    "LOA",
    "LOS",
    "MGA",
    "MGS",
    "WCA",
    "WCS",
    "WOA",
    "WOS",
    "MWA",
    "MWS"
}


# ============================================================
# COMPLETE / SPECIAL GONDOLA CODES
# ============================================================

FULL_CODES = {

    "15FLCA",
    "15FLCS",
    "15FLOA",
    "15FLOS",
    "15FMCA",
    "15FMCS",
    "15FMOA",
    "15FMOS",

    "18FLCA",
    "18FLCS",
    "18FMCA",
    "18FMCS",
    "18FMOA",
    "18FMOS",

    "21FLCA",
    "21FLCS",
    "21FLOA",
    "21FLOS",
    "21FMCA",
    "21FMCS",
    "21FMOA",
    "21FMOS",

    "34FLCA",
    "34FLCS",
    "34FLOA",
    "34FLOS",
    "34FMCA",
    "34FMCS",
    "34FMOA",
    "34FMOS",

    "34HLCA",
    "34HLCS",
    "34HLOA",
    "34HLOS",

    "27HLCA",
    "27HLCS",

    "34SLCA",
    "34SLCS",

    "34RDLC",

    "FLATDECK",
    "FLATDECKWS",

    "36WLOA",
    "36WLOS",
    "36WLCA",
    "36WLCS",
    "15WLOS",

    "36BLOA",
    "36BLOS",
    "36BLCA",
    "36BLCS",

    "15WLCA",
    "15WLCS",
    "15WLOS",
    "15WMCA",
    "15WMCS",

    "12WMCA",
    "12WMCS",

    "15FMWA",
    "15FMWS",
    "21FMWA",
    "21FMWS",
    "34FMWA",
    "34FMWS",

    "12FLCA",
    "12FLCS",
    "12FLOA",
    "12FLOS",
    "12FMCA",
    "12FMCS",
    "12FMOA",
    "12FMOS",

    "36HLCA",
    "36HLCS",
    "36HLOA",
    "36HLOS",

    "34WLOA",
    "34WLOS",
    "34WLCA",
    "34WLCS",

    "32WLOA",
    "32WLOS",
    "32WLCA",
    "32WLCS",

    "30WLOA",
    "30WLOS",
    "30WLCA",
    "30WLCS",

    "27WLOA",
    "27WLOS",
    "27WLCA",
    "27WLCS",

    "21WLOA",
    "21WLOS",
    "21WLCA",
    "21WLCS",

    "12DELC",
    "12DEMO",
    "12ELC",
    "12ELO",
    "12EMC",
    "12EMO",
    "12SELC",
    "12SEMC",

    "15DELC",
    "15DELO",
    "15DEMC",
    "15DEMO",
    "15ELC",
    "15ELO",
    "15ELW",
    "15EMC",
    "15EMM",
    "15EMO",
    "15EMW",
    "15SELC",
    "15SELO",
    "15SEMC",
    "15SEMO",
    "15SEMW",

    "18DELC",
    "18DEMO",
    "18ELC",
    "18ELM",
    "18ELO",
    "18EMC",
    "18EMM",
    "18EMO",
    "18POSTER END",
    "18SELC",
    "18SELO",
    "18SEMC",
    "18SEMO",

    "21DELC",
    "21DELC 200 PEG",
    "21DELM",
    "21DELO",
    "21DEMC",
    "21DEMO",
    "21ELC",
    "21ELM",
    "21ELO",
    "21ELW",
    "21ELWM",
    "21EMC",
    "21EMM",
    "21EMO",
    "21EMW",
    "21EMWM",
    "21POSTER END",
    "21SELC",
    "21SELO",
    "21SELW",
    "21SEMC",
    "21SEMO",
    "21SEMW",

    "26DELW - DIVIDING WALL - END",
    "26EMW - DIVIDING WALL EPF",

    "27ELC",
    "27ELO",
    "27ELW",
    "27EMC",
    "27EMO",
    "27POSTER 540 END",
    "27SELC",
    "27SELO",
    "27SELW",

    "30DELO",
    "30DEMC",
    "30DEMO",
    "30ELC",
    "30ELM",
    "30ELO",
    "30EMC",
    "30EMM",
    "30EMO",
    "30SELC",
    "30SELO",
    "30SELW",
    "30SEMC",
    "30SEMO",

    "32DELC",
    "32DELO",
    "32DEMC",
    "32DEMO",
    "32ELC",
    "32ELM",
    "32ELO",
    "32ELW",
    "32ELWM",
    "32EMC",
    "32EMM",
    "32EMO",
    "32EMW",
    "32EMWM",
    "32SELC",
    "32SELO",
    "32SELW",
    "32SEMC",
    "32SEMO",
    "32SEMW",

    "34DELC",
    "34DELO",
    "34DEMC",
    "34DEMO",
    "34ELC",
    "34ELM",
    "34ELO",
    "34ELW",
    "34ELWM",
    "34EMC",
    "34EMM",
    "34EMO",
    "34EMW",
    "34EMWM",
    "34SELC",
    "34SELO",
    "34SELW",
    "34SEMC",
    "34SEMO",
    "34SEMW",
    "34SELW 540 END",
    "34SEMV 540 END",

    "HALLMARK END 1200",
    "HALLMARK END 900",

    "12QMCA",
    "12QMCS",

    #OLD CODES
"15EPLC",
"15EPMC",
"15EPMO",
"15EPLO",
"15EPMM",

"15SHMC",
"15SHLC",
"15SHLO",

"18EPLC",
"18EPMC",
"18EPMO",
"18EPLO",
"18EPMM",

"18SHMC",
"18SHLC",
"18SHLO",

"21EPLC",
"21EPMC",
"21EPMO",
"21EPLO",
"21EPMM",
"21SHMC",
"21SHLC",
"21SHLO",

"27HLO",

"32EPLC",
"32EPMC",
"32EPMO",
"32EPLO",
"32SHLO",

"34EPLC",
"34EPMC",
"34EPMO",
"34EPLO",
"34SHLO",


"34BLOA",
"34BLOS",

"36BLOA",
"36BLOS",

"15RDLC",
"15RDLO",
"15RDMC",
"15RDMO",

"18RDLC",
"18RDLO",
"18RDMC",
"18RDMO",

"21RDLC",
"21RDLO",
"21RDMC",
"21RDMO",

"32RDLC",
"32RDLO",
"32RDMC",
"32RDMO",

"34RDLC",
"34RDLO",
"34RDMC",
"34RDMO",
"34RELO",

"FLATDECK W/-SURROUND",
"FLATDECK",
"DECK TABLE",
"HOPPER UNIT 2150H",


"HOT SPOT 1500H",
"HOT SPOT COOKBOOKS",
"HOT SPOT 2100H",
"HOT SPOT 3000H",
"HOT SPOT 3200H",
"HOT SPOT 3400H",

"Straight rail",

"6Way",
"16_Way",

"T2 TABLE",
"T2 ARM ONLY",

"HANGER TOTEM",

}


# ============================================================
# NORMALISE CODES
# ============================================================

SIZE_CODES = {
    str(x).upper().strip()
    for x in SIZE_CODES
}

TYPE_CODES = {
    str(x).upper().strip()
    for x in TYPE_CODES
}

FULL_CODES = {
    str(x).upper().strip()
    for x in FULL_CODES
}


# ============================================================
# MATCHING DISTANCE
# ============================================================

MATCH_DIST = 1500.0


# ============================================================
# ANGLE HELPERS
# ============================================================

def normalize_angle(angle):
    """
    Normalize angle to 0 <= angle < 360.
    """

    try:
        angle = float(angle)
    except Exception:
        return 0.0

    angle = angle % 360.0

    if angle < 0:
        angle += 360.0

    return angle


def normalize_line_angle(angle):
    """
    Normalize a line direction to 0 <= angle < 180.

    A line at:
        0°
    and:
        180°

    represents the same physical direction.

    Therefore:

        0°   -> 0°
        180° -> 0°
        270° -> 90°
        360° -> 0°
    """

    angle = normalize_angle(angle)

    angle = angle % 180.0

    if abs(angle - 180.0) < 0.000001:
        angle = 0.0

    if abs(angle) < 0.000001:
        angle = 0.0

    if abs(angle - 90.0) < 0.000001:
        angle = 90.0

    return angle


def get_orientation(rotation_angle):
    """
    Convert an actual angle into a broad orientation category.

    HORIZONTAL:
        approximately 0°

    VERTICAL:
        approximately 90°

    DIAGONAL:
        anything between the two.
    """

    angle = normalize_line_angle(rotation_angle)

    if angle < 25.0 or angle > 155.0:
        return "HORIZONTAL"

    elif 65.0 <= angle <= 115.0:
        return "VERTICAL"

    else:
        return "DIAGONAL"


def get_orientation_from_offset(dx, dy):
    """
    Determine orientation from the physical separation
    between SIZE and TYPE labels.

    This is used for SIZE + TYPE combinations.

    The actual angle is calculated using atan2.
    """

    if abs(dx) < 0.000001 and abs(dy) < 0.000001:
        return "HORIZONTAL"

    angle = math.degrees(
        math.atan2(
            abs(dy),
            abs(dx)
        )
    )

    angle = normalize_line_angle(angle)

    return get_orientation(angle)


def get_angle_from_offset(dx, dy):
    """
    Calculate the physical tracing angle from SIZE -> TYPE.

    Examples:

        dx > 0, dy = 0
            -> 0°

        dx = 0, dy > 0
            -> 90°

        dx > 0, dy > 0
            -> diagonal

    atan2 gives the correct geometric angle.
    """

    if abs(dx) < 0.000001 and abs(dy) < 0.000001:
        return 0.0

    angle = math.degrees(
        math.atan2(
            dy,
            dx
        )
    )

    return normalize_line_angle(angle)


# ============================================================
# BAY RECTANGLE FROM THE DRAWN OUTLINES
# ============================================================

BAY_MIN_SIDE_MM = 250.0
BAY_MAX_SIDE_MM = 4200.0
BAY_SEARCH_MM = 1600.0

# A run of bays is often drawn as one long rectangle, and a wall is
# good evidence of direction too, so long edges are kept. Only sheet
# borders and grid lines are longer than this.
BAY_EDGE_MAX_MM = 40000.0

# Below this the pair of edges found is more likely a shelf line than
# the sides of the bay, so the axis is trusted but the centre is not.
BAY_MIN_CENTRE_MM = 450.0

# No gondola is deeper than this. Without the cap the search for the
# sides of a bay reaches past them to the next row of the run, three
# metres away, and the bay then measures wider across than it is long.
BAY_MAX_DEPTH_MM = 1600.0


def segment_length(seg):
    return math.sqrt(
        (seg[2] - seg[0]) ** 2 +
        (seg[3] - seg[1]) ** 2
    )


def segment_angle(seg):
    return normalize_line_angle(
        math.degrees(
            math.atan2(
                seg[3] - seg[1],
                seg[2] - seg[0]
            )
        )
    )


def line_angle_delta(a, b):
    delta = abs(
        normalize_line_angle(a) -
        normalize_line_angle(b)
    )
    if delta > 90.0:
        delta = 180.0 - delta
    return delta


def point_segment_distance(point, seg):

    """
    Distance from a point to a segment, not to its midpoint.

    A run of bays drawn as one rectangle has edge midpoints metres away
    from any one bay's label, so midpoint distance hides exactly the
    edges that give the bay its direction.
    """

    px, py = float(point[0]), float(point[1])

    x1, y1, x2, y2 = seg[0], seg[1], seg[2], seg[3]

    dx = x2 - x1
    dy = y2 - y1

    span = dx * dx + dy * dy

    if span <= 0.0:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    t = ((px - x1) * dx + (py - y1) * dy) / span

    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0

    return math.sqrt(
        (px - (x1 + t * dx)) ** 2 +
        (py - (y1 + t * dy)) ** 2
    )


class SegmentIndex(object):

    """
    Grid index so each label only tests nearby outline segments.

    Every cell a segment passes through is stamped, not just the cell
    holding its midpoint. A run drawn as one 12 m rectangle has to be
    found from every bay along it.
    """

    def __init__(self, segments, cell=BAY_SEARCH_MM):

        self.cell = float(cell)
        self.cells = {}

        for seg in segments:

            length = segment_length(seg)

            steps = int(length / (self.cell * 0.5)) + 1

            if steps > 400:
                steps = 400

            keys = set()

            for i in range(steps + 1):

                t = float(i) / float(steps)

                x = seg[0] + (seg[2] - seg[0]) * t
                y = seg[1] + (seg[3] - seg[1]) * t

                keys.add((
                    int(math.floor(x / self.cell)),
                    int(math.floor(y / self.cell))
                ))

            for key in keys:
                self.cells.setdefault(key, []).append(seg)

    def near(self, x, y):

        gx = int(math.floor(float(x) / self.cell))
        gy = int(math.floor(float(y) / self.cell))

        out = []
        seen = set()

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for seg in self.cells.get((gx + dx, gy + dy), ()):
                    key = id(seg)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(seg)

        return out


def _dominant_angle(segments):
    buckets = []
    for seg in segments:
        length = segment_length(seg)
        if length <= 0.0:
            continue
        ang = segment_angle(seg)
        placed = False
        for bucket in buckets:
            if line_angle_delta(bucket["angle"], ang) <= 8.0:
                bucket["weight"] += length
                bucket["angles"].append((ang, length))
                placed = True
                break
        if not placed:
            buckets.append({
                "angle": ang,
                "weight": length,
                "angles": [(ang, length)]
            })
    if not buckets:
        return None
    buckets.sort(key=lambda b: b["weight"], reverse=True)
    best = buckets[0]
    x = sum(
        math.cos(math.radians(2.0 * a)) * w
        for a, w in best["angles"]
    )
    y = sum(
        math.sin(math.radians(2.0 * a)) * w
        for a, w in best["angles"]
    )
    return normalize_line_angle(
        math.degrees(math.atan2(y, x)) / 2.0
    )


def _straddling_extent(
    point,
    segments,
    edge_dir_deg,
    measure_dir_deg,
    prefer="outermost",
    max_width=BAY_MAX_SIDE_MM
):

    """
    Distance from point to a parallel edge on each side.

    `prefer` says what the extra parallel lines inside a gondola mean.
    Across the bay they are shelf and kick lines, so the sides of the
    bay are the outermost balanced pair. Along the bay they are the
    divisions between bays, so this bay ends at the nearest pair.

    Also returns how far the two chosen edges run, which is what tells
    a run's long side from the end of a single bay.
    """

    edge_rad = math.radians(edge_dir_deg)
    ux, uy = math.cos(edge_rad), math.sin(edge_rad)
    measure_rad = math.radians(measure_dir_deg)
    nx, ny = math.cos(measure_rad), math.sin(measure_rad)
    px, py = point

    lows = {}
    highs = {}

    for seg in segments:

        mid_x = (seg[0] + seg[2]) / 2.0
        mid_y = (seg[1] + seg[3]) / 2.0

        offset = (mid_x - px) * nx + (mid_y - py) * ny

        extent = abs(
            (seg[2] - seg[0]) * ux +
            (seg[3] - seg[1]) * uy
        )

        if extent < BAY_MIN_SIDE_MM * 0.6:
            continue

        centre_along = (mid_x - px) * ux + (mid_y - py) * uy

        if abs(centre_along) > extent / 2.0 + 200.0:
            continue

        side = lows if offset <= 0.0 else highs

        key = round(offset, 1)

        # Edges at the same offset are one line of the drawing; keep
        # the longest, which says how far that line runs.
        side[key] = max(side.get(key, 0.0), extent)

    if not lows or not highs:
        return None

    near_lows = sorted(lows, reverse=True)[:8]
    near_highs = sorted(highs)[:8]

    pairs = []

    for low in near_lows:
        for high in near_highs:
            width = high - low
            if BAY_MIN_SIDE_MM <= width <= max_width:
                pairs.append((
                    abs(low + high),
                    width,
                    low,
                    high,
                    min(lows[low], highs[high])
                ))

    if not pairs:
        return None

    if prefer == "narrowest":
        pairs.sort(key=lambda p: p[1])
        return pairs[0][2], pairs[0][3], pairs[0][1], pairs[0][4]

    # The label pair straddles the bay centre line, so the sides of the
    # bay sit either side of it at about equal distance. Shelf and kick
    # lines are just as symmetric, so among the balanced pairs take the
    # outermost: that is the outline. Anything reaching across the aisle
    # is lopsided and loses.
    best_balance = min(p[0] for p in pairs)

    balanced = [p for p in pairs if p[0] <= best_balance + 150.0]
    balanced.sort(key=lambda p: p[1], reverse=True)

    return balanced[0][2], balanced[0][3], balanced[0][1], balanced[0][4]


def near_bay_segments(point, segments, search_mm=BAY_SEARCH_MM):

    """
    Drawn edges close enough to the label to belong to its bay.
    """

    near = []

    for seg in segments or ():

        length = segment_length(seg)

        if length < BAY_MIN_SIDE_MM * 0.6 or length > BAY_EDGE_MAX_MM:
            continue

        if point_segment_distance(point, seg) > search_mm:
            continue

        near.append(seg)

    return near


def bay_fit_from_segments(point, segments, search_mm=BAY_SEARCH_MM):

    """
    Read the bay a label sits in from the gondola drawn in the CAD.

    Label positions alone cannot tell a run from the aisle beside it,
    because both have the same spacing. The drawn edges can. Three
    tiers, best first:

        RECTANGLE - long sides and both ends found. Exact centre, axis
                    and bay size.
        DEPTH     - long sides only, which is what a run drawn as one
                    rectangle gives. Exact axis, exact centre across
                    the bay, label position along it.
        EDGE      - direction only. Nothing is moved.

    Returns a dict with x, y, axis and fit, plus length / depth when
    they were measured, or None when no edge is near the label.
    """

    px, py = float(point[0]), float(point[1])

    near = near_bay_segments((px, py), segments, search_mm)

    if not near:
        return None

    dominant = _dominant_angle(near)

    if dominant is None:
        return None

    best = None

    for axis in (dominant, normalize_line_angle(dominant + 90.0)):

        across_dir = normalize_line_angle(axis + 90.0)

        parallel = [
            s for s in near
            if line_angle_delta(segment_angle(s), axis) <= 12.0
        ]

        if not parallel:
            continue

        across = _straddling_extent(
            (px, py),
            parallel,
            axis,
            across_dir,
            "outermost",
            BAY_MAX_DEPTH_MM
        )

        if across is None:
            continue

        # Which of the two candidates is the run direction. The long
        # sides of a run are drawn as one line past many bays, while
        # the ends are a single bay long, so the sides that run further
        # win. Only when they run equally far does the narrower way
        # across decide, which is the long axis of a single bay.
        if best is not None:

            if across[3] < best["across"][3] * 1.3:

                if (across[3] * 1.3 < best["across"][3]
                        or across[2] >= best["across"][2]):
                    continue

        perpendicular = [
            s for s in near
            if line_angle_delta(segment_angle(s), across_dir) <= 12.0
        ]

        along = None

        if perpendicular:
            along = _straddling_extent(
                (px, py),
                perpendicular,
                across_dir,
                axis,
                "narrowest"
            )

        best = {
            "axis": axis,
            "across": across,
            "along": along
        }

    if best is None:
        return {
            "x": round(px, 3),
            "y": round(py, 3),
            "axis": round(dominant, 3),
            "fit": "EDGE"
        }

    axis = best["axis"]
    across_dir = normalize_line_angle(axis + 90.0)

    rad = math.radians(axis)
    ux, uy = math.cos(rad), math.sin(rad)
    across_rad = math.radians(across_dir)
    nx, ny = math.cos(across_rad), math.sin(across_rad)

    cx, cy = px, py
    depth = None
    length = None

    if best["across"][2] >= BAY_MIN_CENTRE_MM:
        across_mid = (best["across"][0] + best["across"][1]) / 2.0
        cx += nx * across_mid
        cy += ny * across_mid
        depth = best["across"][2]

    along = best["along"]

    if along is not None and along[2] >= BAY_MIN_CENTRE_MM:
        along_mid = (along[0] + along[1]) / 2.0
        cx += ux * along_mid
        cy += uy * along_mid
        length = along[2]

    if depth is None:
        fit = "EDGE"
    elif length is None:
        fit = "DEPTH"
    else:
        fit = "RECTANGLE"

    result = {
        "x": round(cx, 3),
        "y": round(cy, 3),
        "axis": round(axis, 3),
        "fit": fit
    }

    # As drawn: length along the axis, depth across it. The axis comes
    # from how far the sides run, so it is not always the longer of the
    # two, and sorting them would misreport a deep bay.
    if length is not None:
        result["length"] = round(length, 1)

    if depth is not None:
        result["depth"] = round(depth, 1)

    return result


# ============================================================
# CREATE COMPLETE CODE ITEM
# ============================================================

def make_full_code_item(
    text,
    x,
    y,
    rotation,
    layer
):
    """
    Creates a gondola item for a complete code that exists
    as one TEXT / MTEXT entity.

    IMPORTANT:
    orientation_angle is now explicitly included.
    """

    tracing_angle = normalize_line_angle(
        rotation
    )

    return {
        "code": text,

        "top": "",
        "bottom": "",

        "x": round(x, 3),
        "y": round(y, 3),

        "rotation": round(rotation, 3),

        # Actual physical DXF tracing direction
        "orientation_angle": round(
            tracing_angle,
            3
        ),

        # Broad classification
        "orientation": get_orientation(
            tracing_angle
        ),

        "pair_dx": 0,
        "pair_dy": 0,

        "layer": layer,

        "pair_dist": 0,

        "detection": "FULL_CODE"
    }


# ============================================================
# MAIN EXTRACTION FUNCTION
# ============================================================

def extract_with_orientation(dxf_path):

    size_texts = []
    type_texts = []
    full_code_gondolas = []
    bay_segments = []

    # Outlines collected while walking modelspace, kept apart so they
    # can be mapped into a block's own coordinates if that is where the
    # labels turn out to live.
    world_segments = []
    block_matrices = {}
    current_bucket = [None]
    current_space = ["MODELSPACE"]
    labels_by_space = {}

    print("Loading DXF file...")
    print(dxf_path)
    print("")

    doc = ezdxf.readfile(
        dxf_path
    )

    print("DXF loaded!")
    print("")


    # ========================================================
    # PROCESS ENTITY
    # ========================================================

    def add_bay_segment(x1, y1, x2, y2):
        """
        Keep only edges that could be the side of a bay or a run. A
        store plan carries far more hatching and detail than outlines,
        and the fit discards the rest anyway.
        """

        length = math.hypot(x2 - x1, y2 - y1)

        if length < BAY_MIN_SIDE_MM * 0.6 or length > BAY_EDGE_MAX_MM:
            return

        seg = (x1, y1, x2, y2)

        bay_segments.append(seg)

        if current_bucket[0] is not None:
            current_bucket[0].append(seg)


    def collect_bay_segments(entity, depth=0):
        """
        Keep the drawn gondola outlines, in the same coordinates as the
        labels. Store planners need the family on the rectangle, and
        label positions alone cannot tell a run from the aisle.

        Nested block references are exploded, because in a real store
        plan the gondola outlines sit inside blocks while the labels
        sit in the space around them. V6 found no outlines at all for
        that reason and fell back to voting.
        """

        try:
            dxftype = entity.dxftype()
        except Exception:
            return

        if dxftype == "INSERT":

            if depth >= 4:
                return

            try:
                children = list(entity.virtual_entities())
            except Exception:
                return

            for child in children:

                try:
                    collect_bay_segments(child, depth + 1)
                except Exception:
                    pass

            return

        try:

            if dxftype == "LINE":

                start = entity.dxf.start
                end = entity.dxf.end

                add_bay_segment(
                    float(start.x), float(start.y),
                    float(end.x), float(end.y)
                )

            elif dxftype == "LWPOLYLINE":

                points = [
                    (float(p[0]), float(p[1]))
                    for p in entity.get_points("xy")
                ]

                if len(points) >= 2:

                    closed = False

                    try:
                        closed = bool(entity.closed)
                    except Exception:
                        closed = False

                    if closed:
                        points.append(points[0])

                    for i in range(len(points) - 1):
                        add_bay_segment(
                            points[i][0], points[i][1],
                            points[i + 1][0], points[i + 1][1]
                        )

            elif dxftype == "POLYLINE":

                points = [
                    (float(v.dxf.location.x), float(v.dxf.location.y))
                    for v in entity.vertices
                ]

                if len(points) >= 2:

                    try:
                        if entity.is_closed:
                            points.append(points[0])
                    except Exception:
                        pass

                    for i in range(len(points) - 1):
                        add_bay_segment(
                            points[i][0], points[i][1],
                            points[i + 1][0], points[i + 1][1]
                        )

            elif dxftype == "SOLID":

                corners = []

                for name in ("vtx0", "vtx1", "vtx2", "vtx3"):
                    try:
                        v = entity.dxf.get(name)
                        corners.append((float(v.x), float(v.y)))
                    except Exception:
                        pass

                for i in range(len(corners)):
                    a = corners[i]
                    b = corners[(i + 1) % len(corners)]
                    add_bay_segment(a[0], a[1], b[0], b[1])

        except Exception:
            pass


    def process_entity(entity):

        collect_bay_segments(entity)

        text = ""
        x = 0.0
        y = 0.0
        rotation = 0.0
        layer = ""


        # ----------------------------------------------------
        # TEXT
        # ----------------------------------------------------

        if entity.dxftype() == "TEXT":

            try:
                text = (
                    entity.dxf.text
                    .strip()
                    .upper()
                )
            except Exception:
                return

            try:
                x = entity.dxf.insert.x
                y = entity.dxf.insert.y
            except Exception:
                return

            try:
                rotation = entity.dxf.get(
                    "rotation",
                    0
                )
            except Exception:
                rotation = 0

            try:
                layer = entity.dxf.layer
            except Exception:
                layer = ""


        # ----------------------------------------------------
        # MTEXT
        # ----------------------------------------------------

        elif entity.dxftype() == "MTEXT":

            try:
                text = (
                    entity.text
                    .strip()
                    .upper()
                )
            except Exception:
                return

            try:
                x = entity.dxf.insert.x
                y = entity.dxf.insert.y
            except Exception:
                return

            try:
                rotation = entity.dxf.get(
                    "rotation",
                    0
                )
            except Exception:
                rotation = 0

            try:
                layer = entity.dxf.layer
            except Exception:
                layer = ""

        else:
            return


        if not text:
            return


        # ====================================================
        # COMPLETE CODE
        # ====================================================

        if text in FULL_CODES:

            full_code_gondolas.append(
                make_full_code_item(
                    text,
                    x,
                    y,
                    rotation,
                    layer
                )
            )

            return


        # ====================================================
        # SIZE / TYPE
        # ====================================================

        item = {

            "text": text,

            "x": round(
                x,
                3
            ),

            "y": round(
                y,
                3
            ),

            "rotation": round(
                rotation,
                3
            ),

            "orientation_angle": round(
                normalize_line_angle(
                    rotation
                ),
                3
            ),

            "orientation": get_orientation(
                rotation
            ),

            "layer": layer
        }


        if text in SIZE_CODES:

            size_texts.append(
                item
            )

        elif text in TYPE_CODES:

            type_texts.append(
                item
            )

        else:
            return

        # Which DXF space the labels came from. The outlines may be in
        # another one, and this says which transform to undo.
        space = current_space[0]

        labels_by_space[space] = labels_by_space.get(space, 0) + 1


    # ========================================================
    # SCAN BLOCK DEFINITIONS / XREFS
    # ========================================================

    print("Scanning XREF blocks...")

    for block_def in doc.blocks:

        try:

            if block_def.name.startswith("*"):
                continue

        except Exception:
            continue

        current_space[0] = block_def.name

        for entity in block_def:

            try:
                process_entity(entity)

            except Exception:
                pass

    current_space[0] = "MODELSPACE"


    # ========================================================
    # SCAN MODELSPACE
    # ========================================================

    print("Scanning modelspace...")

    msp = doc.modelspace()

    # Modelspace outlines are in world coordinates. The labels are
    # often inside a block instead, so remember how each block is
    # placed: that is the exact transform between the two.
    current_bucket[0] = world_segments

    for entity in msp:

        try:

            if entity.dxftype() == "INSERT":

                name = entity.dxf.name

                if name not in block_matrices:
                    block_matrices[name] = entity.matrix44()

        except Exception:
            pass

    for entity in msp:

        try:
            process_entity(entity)

        except Exception:
            pass

    current_bucket[0] = None


    # ========================================================
    # REPORT FOUND LABELS
    # ========================================================

    print("")
    print(
        "Size labels found: {}".format(
            len(size_texts)
        )
    )

    print(
        "Type labels found: {}".format(
            len(type_texts)
        )
    )

    print(
        "Complete codes found: {}".format(
            len(full_code_gondolas)
        )
    )

    print("")


    # ========================================================
    # MATCH SIZE + TYPE
    # ========================================================

    used_indices = set()
    used_sizes = set()

    gondolas = []

    # SIZE + TYPE are two lines of one bay label. Pairing greedily at
    # 1500 mm let a SIZE grab the TYPE of the NEXT bay, which put a
    # family in the aisle. Pair mutual nearest first, then relax, so
    # coverage stays the same but cross-bay pairs are gone.

    def _dist(a, b):
        return math.sqrt(
            (b["x"] - a["x"]) ** 2 +
            (b["y"] - a["y"]) ** 2
        )

    def _nearest_type(size_item, max_dist):
        best_i = None
        best_d = max_dist
        for i, type_item in enumerate(type_texts):
            if i in used_indices:
                continue
            d = _dist(size_item, type_item)
            if d < best_d:
                best_d = d
                best_i = i
        return best_i, best_d

    def _nearest_size(type_item, max_dist):
        best_i = None
        best_d = max_dist
        for i, size_item in enumerate(size_texts):
            if i in used_sizes:
                continue
            d = _dist(type_item, size_item)
            if d < best_d:
                best_d = d
                best_i = i
        return best_i, best_d

    matched_pairs = []

    for max_dist, require_mutual in (
        (800.0, True),
        (MATCH_DIST, True),
        (MATCH_DIST, False),
    ):
        for si, size_item in enumerate(size_texts):
            if si in used_sizes:
                continue
            ti, dist = _nearest_type(size_item, max_dist)
            if ti is None:
                continue
            if require_mutual:
                back, _ = _nearest_size(type_texts[ti], max_dist)
                if back != si:
                    continue
            used_sizes.add(si)
            used_indices.add(ti)
            matched_pairs.append((size_item, type_texts[ti], dist))

    for size_item, type_item, best_dist in matched_pairs:

        sx = size_item["x"]
        sy = size_item["y"]

        if True:

            tx = type_item["x"]
            ty = type_item["y"]


            dx = tx - sx
            dy = ty - sy


            # ------------------------------------------------
            # ACTUAL ANGLE
            # ------------------------------------------------
            #
            # Use the actual geometric relationship between
            # SIZE and TYPE labels.
            #
            # This is particularly important for diagonals.
            #

            pair_angle = get_angle_from_offset(
                dx,
                dy
            )


            orientation = get_orientation(
                pair_angle
            )


            # ------------------------------------------------
            # GONDOLA ITEM
            # ------------------------------------------------

            gondola = {

                "code":
                    size_item["text"] +
                    type_item["text"],

                "top":
                    size_item["text"],

                "bottom":
                    type_item["text"],

                # Bay centre, not the SIZE label. The two label lines
                # straddle the bay centre line, so the SIZE label alone
                # pushed every family off its bay.
                "x":
                    round((sx + tx) / 2.0, 3),

                "y":
                    round((sy + ty) / 2.0, 3),

                # Keep SIZE label rotation
                "rotation":
                    size_item["rotation"],

                # IMPORTANT:
                # Physical tracing angle derived from
                # the SIZE -> TYPE geometry.
                "orientation_angle":
                    round(
                        pair_angle,
                        3
                    ),

                # Human-readable classification
                "orientation":
                    orientation,

                "pair_dx":
                    round(
                        dx,
                        1
                    ),

                "pair_dy":
                    round(
                        dy,
                        1
                    ),

                "layer":
                    size_item["layer"],

                "pair_dist":
                    round(
                        best_dist,
                        1
                    ),

                "detection":
                    "SIZE_TYPE"
            }


            gondolas.append(
                gondola
            )


    # ========================================================
    # ADD COMPLETE CODES
    # ========================================================

    gondolas.extend(
        full_code_gondolas
    )


    # ========================================================
    # SNAP EACH GONDOLA ONTO ITS DRAWN RECTANGLE
    # ========================================================
    #
    # This is what makes the trace overlap the gondola. The label pair
    # gives a point inside the bay; the drawn rectangle gives the exact
    # centre and the exact long axis.

    print(
        "Bay outline segments : {}".format(
            len(bay_segments)
        )
    )

    if bay_segments and gondolas:

        seg_x = [s[0] for s in bay_segments] + [s[2] for s in bay_segments]
        seg_y = [s[1] for s in bay_segments] + [s[3] for s in bay_segments]

        print(
            "Outline X range      : {:.0f} .. {:.0f}".format(
                min(seg_x),
                max(seg_x)
            )
        )

        print(
            "Outline Y range      : {:.0f} .. {:.0f}".format(
                min(seg_y),
                max(seg_y)
            )
        )

        print(
            "Gondola X range      : {:.0f} .. {:.0f}".format(
                min(g["x"] for g in gondolas),
                max(g["x"] for g in gondolas)
            )
        )

        print(
            "Gondola Y range      : {:.0f} .. {:.0f}".format(
                min(g["y"] for g in gondolas),
                max(g["y"] for g in gondolas)
            )
        )

    def snap_to(segments, targets, apply=True):
        """
        Read the bay under each target from `segments`. Returns the fit
        tier counts and the items left with no outline near them.

        With apply False nothing is written, so a candidate transform
        can be measured before it is trusted.
        """

        index = SegmentIndex(segments)

        counts = {}
        missed = []

        for item in targets:

            fit = bay_fit_from_segments(
                (item["x"], item["y"]),
                index.near(item["x"], item["y"])
            )

            if fit is None:
                missed.append(item)
                continue

            kind = fit.get("fit", "EDGE")

            counts[kind] = counts.get(kind, 0) + 1

            if not apply:
                continue

            # The axis is CAD truth in every tier, so take it and keep
            # neighbour voting away from it.
            item["orientation_angle"] = fit["axis"]
            item["orientation"] = get_orientation(fit["axis"])
            item["orientation_source"] = "CAD_" + kind
            item["x"] = fit["x"]
            item["y"] = fit["y"]

            if "depth" in fit:
                item["bay_depth"] = fit["depth"]

            if "length" in fit:
                item["bay_length"] = fit["length"]

        return counts, missed


    fit_counts, missed = snap_to(bay_segments, gondolas)


    # ========================================================
    # SAME GONDOLAS, DIFFERENT DXF SPACE
    # ========================================================
    #
    # The labels are commonly inside a block while the outlines are
    # drawn in modelspace, or the reverse. Their coordinates then look
    # unrelated even though they describe the same floor. The block's
    # own INSERT is the exact transform between the two, so try it
    # rather than guessing an offset.

    if missed and len(missed) > len(gondolas) / 4 and world_segments:

        # Only the blocks the labels actually came from, busiest first.
        candidates = [
            name for name in sorted(
                labels_by_space,
                key=lambda n: labels_by_space[n],
                reverse=True
            )
            if name in block_matrices
        ][:3]

        sample = missed[::max(1, len(missed) // 60)]

        best = None

        for name in candidates:

            try:
                back = block_matrices[name].copy()
                back.inverse()
            except Exception:
                continue

            moved = []

            for seg in world_segments:

                try:
                    a = back.transform((seg[0], seg[1], 0.0))
                    b = back.transform((seg[2], seg[3], 0.0))
                except Exception:
                    moved = []
                    break

                moved.append((a[0], a[1], b[0], b[1]))

            if not moved:
                continue

            counts, still_missed = snap_to(moved, sample, apply=False)

            found = len(sample) - len(still_missed)

            if best is None or found > best["found"]:
                best = {
                    "name": name,
                    "found": found,
                    "sample": len(sample),
                    "segments": moved
                }

        if best is not None and best["found"] > best["sample"] / 2:

            print("")
            print(
                "Labels sit inside block '{}'. Mapping the modelspace "
                "outlines into it.".format(
                    best["name"]
                )
            )

            counts, missed = snap_to(best["segments"], missed)

            for key in counts:
                fit_counts[key] = fit_counts.get(key, 0) + counts[key]

    no_geometry = len(missed)

    print("")

    print(
        "Fitted whole bay     : {}".format(
            fit_counts.get("RECTANGLE", 0)
        )
    )

    print(
        "Fitted run depth     : {}".format(
            fit_counts.get("DEPTH", 0)
        )
    )

    print(
        "Direction from edges : {}".format(
            fit_counts.get("EDGE", 0)
        )
    )

    print(
        "No CAD outline near  : {} of {}".format(
            no_geometry,
            len(gondolas)
        )
    )

    if no_geometry > len(gondolas) / 2:

        print("")
        print("  WARNING")
        print("  Most gondolas have no drawn outline within "
              "{:.0f} mm.".format(BAY_SEARCH_MM))
        print("  Compare the ranges above: if the outlines and the")
        print("  gondolas are in different coordinate ranges, the")
        print("  labels and the geometry are in different DXF spaces")
        print("  and orientation falls back to neighbour voting.")

    print("")


    return gondolas


# ============================================================
# RUN
# ============================================================

print("")
print("=" * 60)
print("  GONDOLA ORIENTATION DETECTOR")
print("  {}".format(SCRIPT_VERSION))
print("=" * 60)
print("")

gondolas = extract_with_orientation(
    DXF_FILE_PATH
)

# Original File1 coverage is kept. Only orientation is rewritten:
# SIZE→TYPE is the label stack, not the bay axis. Neighbour bays
# (1200 / 1500 / 1800 mm) vote for the long axis. Dynamo must read
# revit_angle / angle, never DXF text rotation (almost always 0).
BAY_SPACINGS_MM = (1200.0, 1500.0, 1800.0, 2100.0, 900.0, 2400.0, 600.0)
BAY_SPACING_TOLERANCE_MM = 280.0
NEIGHBOR_SEARCH_MM = 2800.0
INHERIT_ORIENT_DIST_MM = 3200.0
ANGLE_SNAP_DEG = 12.0


def _hypot(dx, dy):
    return math.sqrt(dx * dx + dy * dy)


def _angular_delta(a, b):
    delta = abs(normalize_line_angle(a) - normalize_line_angle(b))
    if delta > 90.0:
        delta = 180.0 - delta
    return delta


def _snap_line_angle(angle, snap=ANGLE_SNAP_DEG):
    angle = normalize_line_angle(angle)
    for target in (0.0, 45.0, 90.0, 135.0):
        if _angular_delta(angle, target) <= snap:
            return target
    return angle


def _is_bay_spacing(dist):
    if dist < 400.0 or dist > NEIGHBOR_SEARCH_MM:
        return False
    for spacing in BAY_SPACINGS_MM:
        if abs(dist - spacing) <= BAY_SPACING_TOLERANCE_MM:
            return True
        if abs(dist - 2.0 * spacing) <= BAY_SPACING_TOLERANCE_MM:
            return True
    return False


def _mean_line_angle(angles):
    if not angles:
        return 0.0
    x = sum(math.cos(math.radians(2.0 * ang)) for ang in angles)
    y = sum(math.sin(math.radians(2.0 * ang)) for ang in angles)
    return normalize_line_angle(math.degrees(math.atan2(y, x)) / 2.0)


def _tracing_to_revit_angle(orientation_angle):
    return normalize_line_angle(normalize_line_angle(orientation_angle) + 90.0)


def apply_neighbor_orientations(items):
    resolved = [None] * len(items)

    # A bay read from the drawn outline is already exact, whichever tier
    # it came from. Never let neighbour voting move it: a run and the
    # aisle beside it share the same 1200 mm spacing, which is what put
    # half the V5 and V6 families 90 degrees out.
    for i, item in enumerate(items):
        source = str(item.get("orientation_source", ""))
        if source.startswith("CAD_"):
            resolved[i] = (
                normalize_line_angle(item.get("orientation_angle", 0.0)),
                source
            )

    for i, target in enumerate(items):
        if resolved[i] is not None:
            continue
        votes = []
        for j, other in enumerate(items):
            if i == j:
                continue
            dx = other["x"] - target["x"]
            dy = other["y"] - target["y"]
            dist = _hypot(dx, dy)
            if not _is_bay_spacing(dist):
                continue
            weight = 2.0 if other["code"][:3] == target["code"][:3] else 1.0
            if other["code"] == target["code"]:
                weight += 1.5
            votes.append((
                weight,
                get_angle_from_offset(dx, dy),
                math.degrees(math.atan2(dy, dx)) % 360.0
            ))
        if not votes:
            continue
        buckets = []
        for weight, ang, bearing in votes:
            placed = False
            for bucket in buckets:
                if _angular_delta(bucket["angle"], ang) <= 15.0:
                    bucket["weight"] += weight
                    bucket["angles"].append(ang)
                    bucket["bearings"].append(bearing)
                    placed = True
                    break
            if not placed:
                buckets.append({
                    "angle": ang,
                    "weight": weight,
                    "angles": [ang],
                    "bearings": [bearing],
                })
        # A run has bays on both sides. The aisle has bays on one side
        # only, so two-sided support is the stronger signal.
        for bucket in buckets:
            first = bucket["bearings"][0]
            opposite = any(
                150.0 <= abs((b - first + 180.0) % 360.0 - 180.0) <= 210.0
                or abs(abs(b - first) - 180.0) <= 30.0
                for b in bucket["bearings"][1:]
            )
            if opposite:
                bucket["weight"] += 3.0
        buckets.sort(key=lambda b: b["weight"], reverse=True)
        if buckets and buckets[0]["weight"] >= 1.0:
            resolved[i] = (_snap_line_angle(_mean_line_angle(buckets[0]["angles"])), "NEIGHBOR_RUN")

    for i, item in enumerate(items):
        if resolved[i] is not None:
            continue
        best = None
        best_dist = INHERIT_ORIENT_DIST_MM
        for j, other in enumerate(items):
            if resolved[j] is None:
                continue
            dist = _hypot(other["x"] - item["x"], other["y"] - item["y"])
            if dist < best_dist:
                best_dist = dist
                best = resolved[j]
        if best is not None:
            resolved[i] = (best[0], "INHERITED_NEIGHBOR")

    for i, item in enumerate(items):
        if resolved[i] is None:
            # SIZE→TYPE is across the bay. Turn it into the long axis.
            fallback = normalize_line_angle(item.get("orientation_angle", 0.0) + 90.0)
            if item.get("detection") == "FULL_CODE":
                fallback = 0.0
            resolved[i] = (_snap_line_angle(fallback), "PAIR_STACK_PERPENDICULAR")
        angle, source = resolved[i]
        item["orientation_angle"] = round(angle, 3)
        item["revit_angle"] = round(_tracing_to_revit_angle(angle), 3)
        item["angle"] = item["revit_angle"]
        item["orientation"] = get_orientation(angle)
        item["orientation_source"] = source
    return items


gondolas = apply_neighbor_orientations(gondolas)

_by_source = {}
for _g in gondolas:
    _key = _g.get("orientation_source", "UNKNOWN")
    _by_source[_key] = _by_source.get(_key, 0) + 1

print("Orientation source:")
for _key in sorted(_by_source):
    print("  {:<28} {}".format(_key, _by_source[_key]))
print("")


# ============================================================
# REPORT
# ============================================================

print("")
print("=" * 60)
print("  GONDOLA ORIENTATION REPORT")
print("=" * 60)
print("")


horizontal = [
    g
    for g in gondolas
    if g["orientation"] == "HORIZONTAL"
]


vertical = [
    g
    for g in gondolas
    if g["orientation"] == "VERTICAL"
]


diagonal = [
    g
    for g in gondolas
    if g["orientation"] == "DIAGONAL"
]


total = len(
    gondolas
)


# ============================================================
# SUMMARY
# ============================================================

print(
    "Total gondolas : {}".format(
        total
    )
)

print(
    "Horizontal     : {} ({:.1f}%)".format(
        len(horizontal),
        len(horizontal) / total * 100
        if total else 0
    )
)

print(
    "Vertical       : {} ({:.1f}%)".format(
        len(vertical),
        len(vertical) / total * 100
        if total else 0
    )
)

print(
    "Diagonal       : {} ({:.1f}%)".format(
        len(diagonal),
        len(diagonal) / total * 100
        if total else 0
    )
)

print("")


# ============================================================
# ORIENTATION LIST
# ============================================================

for label, group, arrow in [

    (
        "HORIZONTAL",
        horizontal,
        "→"
    ),

    (
        "VERTICAL",
        vertical,
        "↑"
    ),

    (
        "DIAGONAL",
        diagonal,
        "↗"
    ),

]:

    print(
        "─" * 60
    )

    print(
        "{} GONDOLAS ({}):".format(
            label,
            arrow
        )
    )

    print(
        "─" * 60
    )


    for g in group:

        print(
            "  {:<30} "
            "x={:>8.0f} "
            "y={:>8.0f} "
            "angle={:>7.2f}° "
            "dist={:>7.1f}mm "
            "[{}]".format(

                g["code"],

                g["x"],

                g["y"],

                g.get(
                    "orientation_angle",
                    0
                ),

                g["pair_dist"],

                g["detection"]
            )
        )


    print("")


# ============================================================
# COUNT BY CODE AND ORIENTATION
# ============================================================

print(
    "─" * 60
)

print(
    "COUNT BY CODE:"
)

print(
    "─" * 60
)


from collections import defaultdict


breakdown = defaultdict(
    lambda: {
        "H": 0,
        "V": 0,
        "D": 0,
        "total": 0
    }
)


for g in gondolas:

    name = g["code"]

    ori = g[
        "orientation"
    ][0]


    breakdown[name][ori] += 1

    breakdown[name]["total"] += 1


print(
    "{:<30} {:>6} {:>6} {:>6} {:>6}".format(
        "Code",
        "Total",
        "H",
        "V",
        "D"
    )
)


print(
    "─" * 58
)


for name in sorted(
    breakdown.keys()
):

    b = breakdown[name]


    print(
        "{:<30} {:>6} {:>6} {:>6} {:>6}".format(

            name,

            b["total"],

            b["H"],

            b["V"],

            b["D"]
        )
    )


# ============================================================
# SAVE JSON
# ============================================================

output = {

    "total":
        len(gondolas),

    "horizontal":
        len(horizontal),

    "vertical":
        len(vertical),

    "diagonal":
        len(diagonal),

    "gondolas":
        gondolas
}


print("")
print("Saving JSON...")


with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=2,
        ensure_ascii=False
    )


print("")
print(
    "Saved to:"
)
print(
    OUTPUT_JSON
)


# ============================================================
# FINAL ANGLE REPORT
# ============================================================

print("")
print("=" * 60)
print("  ACTUAL TRACING ANGLES")
print("=" * 60)
print("")


for g in gondolas:

    print(
        "  {:<30} "
        "orientation={:<10} "
        "angle={:>7.2f}° "
        "x={:>8.0f} "
        "y={:>8.0f}".format(

            g["code"],

            g["orientation"],

            g.get(
                "orientation_angle",
                0
            ),

            g["x"],

            g["y"]
        )
    )


print("")
print("=" * 60)
print("  COMPLETE")
print("=" * 60)