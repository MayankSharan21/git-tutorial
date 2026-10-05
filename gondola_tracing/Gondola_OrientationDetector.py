# Gondola_OrientationDetector.py
#
# Original File1 collector (the run that filled most bays).
# Version 2026-10-05m-original-files
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
SCRIPT_VERSION = "2026-10-05m-original-files"


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

    def process_entity(entity):

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

    gondolas = []


    for size_item in size_texts:

        sx = size_item["x"]
        sy = size_item["y"]

        best = None
        best_dist = MATCH_DIST


        for i, type_item in enumerate(
            type_texts
        ):

            if i in used_indices:
                continue


            tx = type_item["x"]
            ty = type_item["y"]


            dx = tx - sx
            dy = ty - sy


            dist = math.sqrt(
                dx * dx +
                dy * dy
            )


            if dist < best_dist:

                best_dist = dist

                best = (
                    i,
                    type_item
                )


        # ----------------------------------------------------
        # MATCH FOUND
        # ----------------------------------------------------

        if best:

            idx, type_item = best

            used_indices.add(
                idx
            )


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

                "x":
                    sx,

                "y":
                    sy,

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
    for i, target in enumerate(items):
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
            votes.append((weight, get_angle_from_offset(dx, dy)))
        if not votes:
            continue
        buckets = []
        for weight, ang in votes:
            placed = False
            for bucket in buckets:
                if _angular_delta(bucket["angle"], ang) <= 15.0:
                    bucket["weight"] += weight
                    bucket["angles"].append(ang)
                    placed = True
                    break
            if not placed:
                buckets.append({"angle": ang, "weight": weight, "angles": [ang]})
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
print("Orientation rewrite : neighbour-run (original collect kept)")
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