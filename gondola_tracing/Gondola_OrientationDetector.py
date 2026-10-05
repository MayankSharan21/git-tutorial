# Gondola_OrientationDetector.py
#
# Original File1 collector (the run that filled most bays).
# Version 2026-10-05p-bay-fit
#
# Only orientation is corrected after collect:
#   leftover named blocks + modelspace TEXT, MATCH_DIST 1500,
#   family XY = SIZE label. Neighbour-run writes revit_angle.
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
SCRIPT_VERSION = "2026-10-05p-bay-fit"


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


class SegmentIndex(object):

    """
    Grid index so each label only tests nearby outline segments.
    """

    def __init__(self, segments, cell=BAY_SEARCH_MM):
        self.cell = float(cell)
        self.cells = {}
        for seg in segments:
            mid_x = (seg[0] + seg[2]) / 2.0
            mid_y = (seg[1] + seg[3]) / 2.0
            key = (
                int(math.floor(mid_x / self.cell)),
                int(math.floor(mid_y / self.cell))
            )
            self.cells.setdefault(key, []).append(seg)

    def near(self, x, y):
        gx = int(math.floor(float(x) / self.cell))
        gy = int(math.floor(float(y) / self.cell))
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                out.extend(
                    self.cells.get((gx + dx, gy + dy), ())
                )
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


def _straddling_extent(point, segments, edge_dir_deg, measure_dir_deg):
    edge_rad = math.radians(edge_dir_deg)
    ux, uy = math.cos(edge_rad), math.sin(edge_rad)
    measure_rad = math.radians(measure_dir_deg)
    nx, ny = math.cos(measure_rad), math.sin(measure_rad)
    px, py = point

    low = None
    high = None

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
        if offset <= 0.0:
            if low is None or offset > low:
                low = offset
        else:
            if high is None or offset < high:
                high = offset

    if low is None or high is None:
        return None

    width = high - low

    if not (BAY_MIN_SIDE_MM <= width <= BAY_MAX_SIDE_MM):
        return None

    return low, high, width


def bay_rect_from_segments(point, segments, search_mm=BAY_SEARCH_MM):

    """
    Fit the drawn gondola rectangle that holds a label.

    Returns centre, length, depth and long-axis angle, or None.
    """

    px, py = float(point[0]), float(point[1])

    near = []
    for seg in segments or ():
        length = segment_length(seg)
        if length < BAY_MIN_SIDE_MM * 0.6 or length > BAY_MAX_SIDE_MM:
            continue
        mid_x = (seg[0] + seg[2]) / 2.0
        mid_y = (seg[1] + seg[3]) / 2.0
        if abs(mid_x - px) > search_mm or abs(mid_y - py) > search_mm:
            continue
        near.append(seg)

    if len(near) < 2:
        return None

    axis = _dominant_angle(near)

    if axis is None:
        return None

    across_dir = normalize_line_angle(axis + 90.0)

    parallel = [
        s for s in near
        if line_angle_delta(segment_angle(s), axis) <= 12.0
    ]
    perpendicular = [
        s for s in near
        if line_angle_delta(segment_angle(s), across_dir) <= 12.0
    ]

    if not parallel or not perpendicular:
        return None

    across = _straddling_extent((px, py), parallel, axis, across_dir)
    along = _straddling_extent((px, py), perpendicular, across_dir, axis)

    if across is None or along is None:
        return None

    rad = math.radians(axis)
    ux, uy = math.cos(rad), math.sin(rad)
    across_rad = math.radians(across_dir)
    nx, ny = math.cos(across_rad), math.sin(across_rad)

    across_mid = (across[0] + across[1]) / 2.0
    along_mid = (along[0] + along[1]) / 2.0

    cx = px + nx * across_mid + ux * along_mid
    cy = py + ny * across_mid + uy * along_mid

    side_along = along[2]
    side_across = across[2]

    if side_along >= side_across:
        long_axis = axis
        length, depth = side_along, side_across
    else:
        long_axis = across_dir
        length, depth = side_across, side_along

    return {
        "x": round(cx, 3),
        "y": round(cy, 3),
        "length": round(length, 1),
        "depth": round(depth, 1),
        "axis": round(long_axis, 3),
    }


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

    def collect_bay_segments(entity):
        """
        Keep the drawn gondola outlines, in the same coordinates as the
        labels. Store planners need the family on the rectangle, and
        label positions alone cannot tell a run from the aisle.
        """

        try:
            dxftype = entity.dxftype()
        except Exception:
            return

        try:

            if dxftype == "LINE":

                start = entity.dxf.start
                end = entity.dxf.end

                bay_segments.append((
                    float(start.x), float(start.y),
                    float(end.x), float(end.y)
                ))

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
                        bay_segments.append((
                            points[i][0], points[i][1],
                            points[i + 1][0], points[i + 1][1]
                        ))

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
                        bay_segments.append((
                            points[i][0], points[i][1],
                            points[i + 1][0], points[i + 1][1]
                        ))

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
                    bay_segments.append((a[0], a[1], b[0], b[1]))

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


        for entity in block_def:

            try:
                process_entity(entity)

            except Exception:
                pass


    # ========================================================
    # SCAN MODELSPACE
    # ========================================================

    print("Scanning modelspace...")

    msp = doc.modelspace()

    for entity in msp:

        try:
            process_entity(entity)

        except Exception:
            pass


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

    index = SegmentIndex(bay_segments)

    snapped = 0

    for g in gondolas:

        rect = bay_rect_from_segments(
            (g["x"], g["y"]),
            index.near(g["x"], g["y"])
        )

        if rect is None:
            continue

        g["x"] = rect["x"]
        g["y"] = rect["y"]
        g["bay_length"] = rect["length"]
        g["bay_depth"] = rect["depth"]
        g["orientation_angle"] = rect["axis"]
        g["orientation"] = get_orientation(rect["axis"])
        g["orientation_source"] = "CAD_RECTANGLE"

        snapped += 1

    print(
        "Snapped to CAD bay   : {} of {}".format(
            snapped,
            len(gondolas)
        )
    )
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

    # A bay matched to its drawn rectangle is already exact. Never let
    # neighbour voting move it: a run and the aisle beside it share the
    # same 1200 mm spacing, which is what put half the V5 families 90
    # degrees out.
    for i, item in enumerate(items):
        if item.get("orientation_source") == "CAD_RECTANGLE":
            resolved[i] = (
                normalize_line_angle(item.get("orientation_angle", 0.0)),
                "CAD_RECTANGLE"
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