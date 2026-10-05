"""
Shared gondola tracing helpers.

Used by Gondola_OrientationDetector.py and the unit tests.
Dynamo cannot import this file, so the placement script stays standalone.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict


# ---------------------------------------------------------------------------
# Catalogues
# ---------------------------------------------------------------------------

SIZE_CODES = {
    "15F", "21F", "34F", "34H", "34S", "36W", "36B", "18F", "12W", "15W",
    "27H", "28F", "42F", "21H", "12F", "36H", "34W", "32W", "30W", "27W",
    "21W", "12Q", "26", "27", "30", "32", "34B",
}

TYPE_CODES = {
    "MCA", "MCS", "LCA", "LCS", "MOA", "MOS", "LOA", "LOS", "MGA", "MGS",
    "WCA", "WCS", "WOA", "WOS", "MWA", "MWS",
}

FULL_CODES = {
    "15FLCA", "15FLCS", "15FLOA", "15FLOS", "15FMCA", "15FMCS", "15FMOA", "15FMOS",
    "18FLCA", "18FLCS", "18FMCA", "18FMCS", "18FMOA", "18FMOS",
    "21FLCA", "21FLCS", "21FLOA", "21FLOS", "21FMCA", "21FMCS", "21FMOA", "21FMOS",
    "34FLCA", "34FLCS", "34FLOA", "34FLOS", "34FMCA", "34FMCS", "34FMOA", "34FMOS",
    "34HLCA", "34HLCS", "34HLOA", "34HLOS",
    "27HLCA", "27HLCS",
    "34SLCA", "34SLCS",
    "34RDLC",
    "FLATDECK", "FLATDECKWS",
    "36WLOA", "36WLOS", "36WLCA", "36WLCS", "15WLOS",
    "36BLOA", "36BLOS", "36BLCA", "36BLCS",
    "15WLCA", "15WLCS", "15WLOS", "15WMCA", "15WMCS",
    "12WMCA", "12WMCS",
    "15FMWA", "15FMWS", "21FMWA", "21FMWS", "34FMWA", "34FMWS",
    "12FLCA", "12FLCS", "12FLOA", "12FLOS", "12FMCA", "12FMCS", "12FMOA", "12FMOS",
    "36HLCA", "36HLCS", "36HLOA", "36HLOS",
    "34WLOA", "34WLOS", "34WLCA", "34WLCS",
    "32WLOA", "32WLOS", "32WLCA", "32WLCS",
    "30WLOA", "30WLOS", "30WLCA", "30WLCS",
    "27WLOA", "27WLOS", "27WLCA", "27WLCS",
    "21WLOA", "21WLOS", "21WLCA", "21WLCS",
    "12DELC", "12DEMO", "12ELC", "12ELO", "12EMC", "12EMO", "12SELC", "12SEMC",
    "15DELC", "15DELO", "15DEMC", "15DEMO", "15ELC", "15ELO", "15ELW", "15EMC",
    "15EMM", "15EMO", "15EMW", "15SELC", "15SELO", "15SEMC", "15SEMO", "15SEMW",
    "18DELC", "18DEMO", "18ELC", "18ELM", "18ELO", "18EMC", "18EMM", "18EMO",
    "18POSTER END", "18SELC", "18SELO", "18SEMC", "18SEMO",
    "21DELC", "21DELC 200 PEG", "21DELM", "21DELO", "21DEMC", "21DEMO", "21ELC",
    "21ELM", "21ELO", "21ELW", "21ELWM", "21EMC", "21EMM", "21EMO", "21EMW",
    "21EMWM", "21POSTER END", "21SELC", "21SELO", "21SELW", "21SEMC", "21SEMO",
    "21SEMW",
    "26DELW - DIVIDING WALL - END", "26EMW - DIVIDING WALL EPF",
    "27ELC", "27ELO", "27ELW", "27EMC", "27EMO", "27POSTER 540 END",
    "27SELC", "27SELO", "27SELW",
    "30DELO", "30DEMC", "30DEMO", "30ELC", "30ELM", "30ELO", "30EMC", "30EMM",
    "30EMO", "30SELC", "30SELO", "30SELW", "30SEMC", "30SEMO",
    "32DELC", "32DELO", "32DEMC", "32DEMO", "32ELC", "32ELM", "32ELO", "32ELW",
    "32ELWM", "32EMC", "32EMM", "32EMO", "32EMW", "32EMWM", "32SELC", "32SELO",
    "32SELW", "32SEMC", "32SEMO", "32SEMW",
    "34DELC", "34DELO", "34DEMC", "34DEMO", "34ELC", "34ELM", "34ELO", "34ELW",
    "34ELWM", "34EMC", "34EMM", "34EMO", "34EMW", "34EMWM", "34SELC", "34SELO",
    "34SELW", "34SEMC", "34SEMO", "34SEMW", "34SELW 540 END", "34SEMV 540 END",
    "HALLMARK END 1200", "HALLMARK END 900",
    "12QMCA", "12QMCS",
    "15EPLC", "15EPMC", "15EPMO", "15EPLO", "15EPMM",
    "15SHMC", "15SHLC", "15SHLO",
    "18EPLC", "18EPMC", "18EPMO", "18EPLO", "18EPMM",
    "18SHMC", "18SHLC", "18SHLO",
    "21EPLC", "21EPMC", "21EPMO", "21EPLO", "21EPMM",
    "21SHMC", "21SHLC", "21SHLO",
    "27HLO",
    "32EPLC", "32EPMC", "32EPMO", "32EPLO", "32SHLO",
    "34EPLC", "34EPMC", "34EPMO", "34EPLO", "34SHLO",
    "34BLOA", "34BLOS",
    "36BLOA", "36BLOS",
    "15RDLC", "15RDLO", "15RDMC", "15RDMO",
    "18RDLC", "18RDLO", "18RDMC", "18RDMO",
    "21RDLC", "21RDLO", "21RDMC", "21RDMO",
    "32RDLC", "32RDLO", "32RDMC", "32RDMO",
    "34RDLC", "34RDLO", "34RDMC", "34RDMO", "34RELO",
    "FLATDECK W/-SURROUND", "DECK TABLE", "HOPPER UNIT 2150H",
    "HOT SPOT 1500H", "HOT SPOT COOKBOOKS", "HOT SPOT 2100H",
    "HOT SPOT 3000H", "HOT SPOT 3200H", "HOT SPOT 3400H",
    "STRAIGHT RAIL", "6WAY", "16_WAY",
    "T2 TABLE", "T2 ARM ONLY", "T2 NO RAIL/ARMS", "T3 TABLE",
    "HANGER TOTEM",
    "15WLOA",
    "27SHLO",
    "LRD", "LRD_2",
}

# Incoming DXF text -> canonical catalogue code.
CODE_ALIASES = {
    "6 WAY": "6WAY",
    "6-WAY": "6WAY",
    "6_WAY": "6WAY",
    "16 WAY": "16_WAY",
    "16WAY": "16_WAY",
    "16-WAY": "16_WAY",
    "STRAIGHT-RAIL": "STRAIGHT RAIL",
    "STRAIGHTRAIL": "STRAIGHT RAIL",
    "FLATDECKWS": "FLATDECK W/-SURROUND",
    "FLATDECK WS": "FLATDECK W/-SURROUND",
    "FLATDECK W/ SURROUND": "FLATDECK W/-SURROUND",
    "FLAT DECK": "FLATDECK",
    "T2TABLE": "T2 TABLE",
    "T2-TABLE": "T2 TABLE",
    "T2 ARM": "T2 ARM ONLY",
    "T2 NORAIL/ARMS": "T2 NO RAIL/ARMS",
    "T2 NO RAIL ARMS": "T2 NO RAIL/ARMS",
    "T3TABLE": "T3 TABLE",
    "LRD": "FLATDECK",
    "LRD2": "FLATDECK W/-SURROUND",
    "LRD_2": "FLATDECK W/-SURROUND",
    "15DEMODE": "15DEMO",
    "18DEMODE": "18DEMO",
    "21DEMODE": "21DEMO",
    "27SHLO": "27SHLO",
}

# Notes printed next to bays. These are not gondolas.
IGNORE_LABELS = {
    "DE", "RD", "VM", "PRICE", "MAN", "NO EPF", "NOEPF",
    "CLADDED SURROUND", "CLADDED", "SURROUND",
    "FIXTURE FIXED TO FLOOR", "SEAT", "MIRROR", "BR", "DP", "PS",
    "ENTRY", "EXIT", "FHR", "HYDRANT", "C.H", "CH",
    "(VM)", "(PRICE)", "(MAN)", "NO VM RAIL",
    "2X(595X1195)", "390", "WEIGHTS",
    "SHOWCASE", "CPV UNIT", "ENERGIZER UNIT", "ENERGIZER",
    "BULK GOODS BOARD", "FIXTURE CLASHES WITH COLUMN",
    "CUT ON SITE", "NO EPF",
}

EXISTING_LAYER_HINTS = ("EXIST", "EXG", "AS-BUILT", "ASBUILT", "X-EXIST")
PROPOSED_LAYER_HINTS = ("PROPOS", "NEW SELL", "NEW-SELL", "SELLING FLOOR", "FUTURE")

PHRASE_JOINS = (
    (("STRAIGHT", "RAIL"), "STRAIGHT RAIL"),
    (("FLATDECK", "W/-SURROUND"), "FLATDECK W/-SURROUND"),
    (("FLATDECK", "W/- SURROUND"), "FLATDECK W/-SURROUND"),
    (("HOPPER", "UNIT 2150H"), "HOPPER UNIT 2150H"),
    (("HOT SPOT", "1500H"), "HOT SPOT 1500H"),
    (("HOT SPOT", "2100H"), "HOT SPOT 2100H"),
    (("HOT SPOT", "3000H"), "HOT SPOT 3000H"),
    (("HOT SPOT", "3200H"), "HOT SPOT 3200H"),
    (("HOT SPOT", "3400H"), "HOT SPOT 3400H"),
    (("HOT SPOT", "COOKBOOKS"), "HOT SPOT COOKBOOKS"),
    (("T2", "NO RAIL/ARMS"), "T2 NO RAIL/ARMS"),
    (("T2 NO", "RAIL/ARMS"), "T2 NO RAIL/ARMS"),
    (("T3", "TABLE"), "T3 TABLE"),
)

OVERLAP_DEDUP_MM = 350.0

# Typical bay centres along a gondola run, millimetres.
BAY_SPACINGS_MM = (1200.0, 1500.0, 1800.0, 2100.0, 900.0, 2400.0, 600.0)
BAY_SPACING_TOLERANCE_MM = 280.0
NEIGHBOR_SEARCH_MM = 2800.0
TIGHT_PAIR_DIST_MM = 700.0
LOOSE_PAIR_DIST_MM = 1100.0
DEDUP_DIST_MM = 80.0
INHERIT_ORIENT_DIST_MM = 3200.0
ANGLE_SNAP_DEG = 12.0


def _freeze_catalogues():
    global SIZE_CODES, TYPE_CODES, FULL_CODES
    SIZE_CODES = {str(x).upper().strip() for x in SIZE_CODES}
    TYPE_CODES = {str(x).upper().strip() for x in TYPE_CODES}
    FULL_CODES = {str(x).upper().strip() for x in FULL_CODES}

    # Pull extra size/type tokens out of complete codes such as 12QMCA.
    size_pat = re.compile(r"^(\d{2}[A-Z])")
    for code in list(FULL_CODES):
        compact = re.sub(r"[^A-Z0-9]", "", code)
        match = size_pat.match(compact)
        if not match:
            continue
        size = match.group(1)
        rest = compact[len(size):]
        if len(size) == 3:
            SIZE_CODES.add(size)
        if 2 <= len(rest) <= 4:
            TYPE_CODES.add(rest)


_freeze_catalogues()


# ---------------------------------------------------------------------------
# Text cleanup
# ---------------------------------------------------------------------------

_MTEXT_GROUP = re.compile(r"\{[^}]*;")
_MTEXT_CODE = re.compile(r"\\[A-Za-z]+[^;\\]*;")
_MULTI_SPACE = re.compile(r"\s+")


def strip_mtext_codes(text):
    """Remove AutoCAD MTEXT formatting and keep readable characters."""
    if text is None:
        return ""

    text = str(text)
    text = text.replace("\\P", "\n").replace("\\p", "\n")
    text = text.replace("\\~", " ")
    text = _MTEXT_GROUP.sub("", text)
    text = _MTEXT_CODE.sub("", text)
    text = text.replace("{", "").replace("}", "")
    text = text.replace("%%U", "").replace("%%u", "")
    text = text.replace("%%C", "").replace("%%c", "")
    return text.strip()


def normalize_code(text):
    """Uppercase, strip formatting, collapse whitespace."""
    cleaned = strip_mtext_codes(text)
    cleaned = cleaned.upper().replace("\n", " ")
    cleaned = cleaned.replace("–", "-").replace("—", "-")
    cleaned = _MULTI_SPACE.sub(" ", cleaned).strip()
    return cleaned


def compact_code(text):
    return re.sub(r"[^A-Z0-9]", "", normalize_code(text))


def canonical_code(text):
    """Map a raw label onto a catalogue code when possible."""
    norm = normalize_code(text)
    if not norm:
        return ""
    if norm in CODE_ALIASES:
        return CODE_ALIASES[norm]
    if norm in FULL_CODES:
        return norm

    compact = compact_code(norm)
    compact_aliases = {
        compact_code(src): dst
        for src, dst in CODE_ALIASES.items()
    }
    if compact in compact_aliases:
        return compact_aliases[compact]
    if compact in FULL_CODES:
        return compact

    # Allow a known full code plus trailing notes: "15FMCA EXISTING".
    for code in sorted(FULL_CODES, key=len, reverse=True):
        code_c = compact_code(code)
        if compact.startswith(code_c) and len(compact) <= len(code_c) + 8:
            return code
        if compact.endswith(code_c) and len(compact) <= len(code_c) + 8:
            return code
    return norm


# ---------------------------------------------------------------------------
# Angle helpers
# ---------------------------------------------------------------------------

def normalize_angle(angle):
    try:
        angle = float(angle)
    except (TypeError, ValueError):
        return 0.0
    angle = angle % 360.0
    if angle < 0:
        angle += 360.0
    return angle


def normalize_line_angle(angle):
    """Fold a direction onto 0 <= angle < 180. 0 and 180 are the same line."""
    angle = normalize_angle(angle) % 180.0
    if abs(angle - 180.0) < 1e-6 or abs(angle) < 1e-6:
        return 0.0
    if abs(angle - 90.0) < 1e-6:
        return 90.0
    return angle


def angle_from_offset(dx, dy):
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return 0.0
    return normalize_line_angle(math.degrees(math.atan2(dy, dx)))


def angular_delta(a, b):
    """Smallest difference between two undirected line angles, 0..90."""
    d = abs(normalize_line_angle(a) - normalize_line_angle(b))
    return min(d, 180.0 - d)


def snap_line_angle(angle, snap=ANGLE_SNAP_DEG):
    angle = normalize_line_angle(angle)
    for target in (0.0, 45.0, 90.0, 135.0):
        if angular_delta(angle, target) <= snap:
            return target
    return angle


def get_orientation(rotation_angle):
    """
    Classify a long-axis angle.

    0° / 180° -> HORIZONTAL
    90°       -> VERTICAL
    else      -> DIAGONAL

    135° is diagonal, not vertical. The previous detector treated any
    angle > 65° as vertical, which flipped NW-SE runs.
    """
    angle = normalize_line_angle(rotation_angle)
    if angular_delta(angle, 0.0) <= 25.0:
        return "HORIZONTAL"
    if angular_delta(angle, 90.0) <= 25.0:
        return "VERTICAL"
    return "DIAGONAL"


def tracing_to_revit_angle(orientation_angle):
    """
    Convert gondola long-axis (0=+X, 90=+Y) into Revit family rotation.

    The store families sit along +Y at 0°. Adding 90° and folding back
    onto 0-180 reproduces the established convention:

        HORIZONTAL -> 90°
        VERTICAL   -> 0°
        45° run    -> 135°
        135° run   -> 45°
    """
    return normalize_line_angle(orientation_angle + 90.0)


def pick_json_angle(item, use_json_angle=True):
    """
    Dynamo-equivalent angle reader.

    Prefer explicit placement angles. Never treat DXF text `rotation`
    as the family rotation — that field is almost always 0 because
    labels stay readable.
    """
    if not use_json_angle:
        return None

    for key in ("revit_angle", "angle", "orientation_angle"):
        if key not in item or item[key] is None:
            continue
        try:
            value = float(item[key])
        except (TypeError, ValueError):
            continue
        if key == "orientation_angle":
            return tracing_to_revit_angle(value)
        return normalize_angle(value)
    return None


# ---------------------------------------------------------------------------
# Label identification
# ---------------------------------------------------------------------------

def is_noise_label(text):
    """True for dimension / VM / overlay notes that are not fixtures."""
    raw = normalize_code(text)
    if not raw:
        return True
    compact = compact_code(raw)
    if raw in IGNORE_LABELS or compact in IGNORE_LABELS:
        return True
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return True
    if re.fullmatch(r"2X\([^)]+\)", compact):
        return True
    if raw.startswith("FSD-") or raw.startswith("FSD "):
        return True
    if "MODS VM" in raw or raw.endswith(" SQM") or raw.endswith(" M²"):
        return True
    return False


def classify_revit_name(name):
    """
    Classify a level, view, CAD, layer, or block name.

    existing — existing-conditions content
    proposed — proposed / selling-floor content
    overlay  — existing and proposed together (do not place here)
    neutral  — no hint
    """
    text = str(name or "").strip().lower()
    if not text:
        return "neutral"
    if "overlay" in text:
        return "overlay"
    if "existing" in text and "proposed" in text:
        return "overlay"
    if "proposed" in text or "selling floor" in text or "selling-floor" in text:
        return "proposed"
    if any(hint.lower() in text for hint in EXISTING_LAYER_HINTS):
        return "existing"
    if "as built" in text or "as-built" in text:
        return "existing"
    if any(hint.lower() in text for hint in PROPOSED_LAYER_HINTS):
        return "proposed"
    return "neutral"


def is_proposed_scope(name):
    return classify_revit_name(name) in ("proposed", "overlay")


def compact_revit_name(name):
    return re.sub(r"[^A-Z0-9]+", "", str(name or "").upper())


def is_existing_conditions_view(name):
    """True for Existing Conditions plans. Never Proposed / Overlay / selling floor."""
    if classify_revit_name(name) != "existing":
        return False
    return "CONDITION" in compact_revit_name(name)


def is_existing_ground_view(name):
    if not is_existing_conditions_view(name):
        return False
    key = compact_revit_name(name)
    return "GROUND" in key or key.endswith("G")


def choose_existing_level_name(level_names, preferred=""):
    """Pick an Existing level. Never returns a proposed or overlay name."""
    names = [str(name) for name in level_names if name]
    preferred_l = str(preferred or "").strip().lower()

    def allowed(name):
        return classify_revit_name(name) not in ("proposed", "overlay")

    for name in names:
        if name.strip().lower() == preferred_l and allowed(name):
            return name
    for name in names:
        if classify_revit_name(name) == "existing" and "ground" in name.lower():
            return name
    for name in names:
        if classify_revit_name(name) == "existing":
            return name
    for name in names:
        if name.strip().lower() == preferred_l and allowed(name):
            return name
    return None


def existing_view_score(view_name, view_level="", preferred_level=""):
    """
    Rank floor plans for Existing-only placement.

    Only Existing Conditions views score. Proposed, selling-floor, and
    overlay names are always 0.
    """
    if not is_existing_conditions_view(view_name):
        return 0
    score = 90
    if is_existing_ground_view(view_name):
        score = 100
    if preferred_level and str(view_level) == str(preferred_level):
        score += 5
    return score


def choose_existing_view_name(views, level_name=""):
    """
    views: iterable of (view_name, view_level_name)

    Pick the Existing Conditions view first. Do not require it to sit
    on 00-GROUND. Never returns an overlay or proposed view name.
    """
    best_name = None
    best_score = 0
    for view_name, view_level in views:
        score = existing_view_score(view_name, view_level, level_name)
        if score > best_score:
            best_score = score
            best_name = str(view_name)
    return best_name


def choose_existing_placement(views, level_names, preferred_level="", preferred_view=""):
    """
    View-first placement.

    Returns (view_name, level_name). The level is the associated level
    of the Existing Conditions view so families actually appear there.
    """
    views = [(str(v), str(l)) for v, l in views if v]
    if preferred_view:
        preferred_l = str(preferred_view).strip().lower()
        for view_name, view_level in views:
            if view_name.strip().lower() == preferred_l:
                if classify_revit_name(view_name) not in ("proposed", "overlay"):
                    return view_name, view_level

    view_name = choose_existing_view_name(views, preferred_level)
    if view_name:
        for name, level in views:
            if name == view_name:
                return name, level

    return None, choose_existing_level_name(level_names, preferred_level)


def layer_bucket(layer):
    scope = classify_revit_name(layer)
    if scope == "existing":
        return "existing"
    if scope in ("proposed", "overlay"):
        return "proposed"
    return "unknown"


def filter_proposed_layers(raw_labels, existing_only=True):
    """
    Tracing is Existing-only. Proposed / overlay layers are dropped
    when other labels remain. Untagged layers are kept.

    If every label sits on a proposed-named layer, keep them. Existing
    Conditions exports often put the real store text on a layer called
    PROPOSED / SELLING FLOOR. Dropping that set writes an empty JSON.
    """
    buckets = defaultdict(list)
    for label in raw_labels:
        buckets[layer_bucket(label.get("layer", ""))].append(label)

    if not existing_only:
        return list(raw_labels), {
            "dropped_proposed_layer": 0,
            "kept_existing_layer": len(raw_labels),
        }

    if buckets["proposed"]:
        kept = buckets["existing"] + buckets["unknown"]
        if not kept:
            return list(raw_labels), {
                "dropped_proposed_layer": 0,
                "kept_existing_layer": len(raw_labels),
            }
        return kept, {
            "dropped_proposed_layer": len(buckets["proposed"]),
            "kept_existing_layer": len(kept),
        }
    return list(raw_labels), {
        "dropped_proposed_layer": 0,
        "kept_existing_layer": len(raw_labels),
    }


def label_source_scope(label):
    """Scope from the INSERT / leftover block name, then the layer."""
    block_scope = classify_revit_name(label.get("block") or "")
    if block_scope in ("existing", "proposed", "overlay"):
        return block_scope
    return classify_revit_name(label.get("layer") or "")


def keep_existing_source_labels(labels, existing_only=True):
    """
    Prefer labels from existing-named INSERTs / leftover blocks.

    Do not return empty just because the only XREF is named
    Selling floor or Overlay. Those files often hold the actual
    existing-plan codes.
    """
    if not existing_only or not labels:
        return list(labels), {
            "dropped_proposed_source": 0,
            "kept_source": len(labels or []),
        }

    buckets = defaultdict(list)
    for label in labels:
        buckets[label_source_scope(label)].append(label)

    existing = buckets["existing"]
    overlay = buckets["overlay"]
    proposed = buckets["proposed"]
    neutral = buckets["neutral"]

    if existing:
        kept = existing + neutral
        return kept, {
            "dropped_proposed_source": len(proposed) + len(overlay),
            "kept_source": len(kept),
        }

    if overlay or neutral:
        if proposed:
            kept = overlay + neutral
            return kept, {
                "dropped_proposed_source": len(proposed),
                "kept_source": len(kept),
            }
        kept = overlay + neutral
        return kept, {
            "dropped_proposed_source": 0,
            "kept_source": len(kept),
        }

    return list(labels), {
        "dropped_proposed_source": 0,
        "kept_source": len(labels),
    }


def has_classified_gondola(labels):
    """True when any raw label is a SIZE, TYPE, PAIR, or FULL code."""
    for label in labels or []:
        if identify_text(label.get("text", "")):
            return True
    return False


def should_scan_leftover(labels):
    """Scan leftover blocks only when modelspace has no gondola codes."""
    return not has_classified_gondola(labels)


def is_layout_block(name):
    text = str(name or "").strip().lower()
    if not text:
        return True
    return (
        text.startswith("*model_space")
        or text.startswith("*paper_space")
        or text in ("*model_space", "*paper_space")
    )


def should_apply_cad_translation(xs, cad_x_mm, pad_mm=80000.0):
    """
    False when JSON XY is already in the same space as the Revit CAD link.

    Marrickville leftover / XREF labels come out near 275000 mm. Adding
    the Existing Conditions link offset (also ~275000 mm) again draws a
    second store to the right of the CAD.
    """
    if not xs:
        return True
    try:
        cad_x_mm = float(cad_x_mm)
    except (TypeError, ValueError):
        return True
    if abs(cad_x_mm) < 1000.0:
        return abs(cad_x_mm) >= 1.0

    values = []
    for x in xs:
        try:
            values.append(float(x))
        except (TypeError, ValueError):
            continue
    if not values:
        return True

    min_x = min(values)
    return not (cad_x_mm - pad_mm <= min_x <= cad_x_mm + 250000.0)


def load_gondola_items(data):
    """Accept {gondolas: [...]} or a bare list from older detector runs."""
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("gondolas", "items", "data"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []


def merge_nearby_phrases(raw_labels, dist=550.0):
    """Join split notes such as STRAIGHT + RAIL or FLATDECK + W/-SURROUND."""
    used = set()
    merged = []
    for i, first in enumerate(raw_labels):
        if i in used:
            continue
        first_text = normalize_code(first.get("text", ""))
        joined = False
        for j, second in enumerate(raw_labels):
            if j <= i or j in used:
                continue
            if hypot(first["x"] - second["x"], first["y"] - second["y"]) > dist:
                continue
            second_text = normalize_code(second.get("text", ""))
            for (left, right), canon in PHRASE_JOINS:
                pair = {first_text, second_text}
                if pair == {left, right}:
                    record = dict(first)
                    record["text"] = canon
                    record["x"] = (first["x"] + second["x"]) / 2.0
                    record["y"] = (first["y"] + second["y"]) / 2.0
                    merged.append(record)
                    used.add(i)
                    used.add(j)
                    joined = True
                    break
            if joined:
                break
        if not joined:
            merged.append(first)
    return merged


def identify_text(text):
    """
    Return a classification tuple:

        ("FULL", code)
        ("SIZE", size)
        ("TYPE", type)
        ("PAIR", size, type)
        None
    """
    raw = normalize_code(text)
    if not raw or is_noise_label(raw):
        return None

    canon = canonical_code(raw)
    if canon in FULL_CODES:
        return ("FULL", canon)

    if raw in SIZE_CODES:
        return ("SIZE", raw)
    if raw in TYPE_CODES:
        return ("TYPE", raw)

    compact = compact_code(raw)
    if compact in SIZE_CODES:
        return ("SIZE", compact)
    if compact in TYPE_CODES:
        return ("TYPE", compact)

    # "15F MCA" / "15F-MCA" / "15FMCA" that is not already a full code.
    tokens = raw.replace("-", " ").split()
    if len(tokens) == 2 and tokens[0] in SIZE_CODES and tokens[1] in TYPE_CODES:
        joined = tokens[0] + tokens[1]
        if joined in FULL_CODES or True:
            return ("PAIR", tokens[0], tokens[1])

    for size in sorted(SIZE_CODES, key=len, reverse=True):
        if compact.startswith(size):
            rest = compact[len(size):]
            if rest in TYPE_CODES:
                joined = size + rest
                if joined in FULL_CODES:
                    return ("FULL", joined)
                return ("PAIR", size, rest)
    return None


def expand_raw_labels(raw_labels):
    """
    Turn DXF-like records into classified labels.

    A multiline MTEXT such as "15F\\PMCA" becomes either one FULL code
    or a SIZE + TYPE pair sharing the insert point.
    """
    expanded = []
    for raw in raw_labels:
        text = strip_mtext_codes(raw.get("text", ""))
        lines = [normalize_code(part) for part in text.splitlines()]
        lines = [part for part in lines if part]
        rotation = float(raw.get("rotation", 0) or 0)
        record = {
            "x": float(raw.get("x", 0) or 0),
            "y": float(raw.get("y", 0) or 0),
            "rotation": rotation,
            "layer": raw.get("layer", "") or "",
        }

        if len(lines) >= 2:
            joined = "".join(lines)
            identified = identify_text(joined) or identify_text(" ".join(lines))
            if identified and identified[0] == "FULL":
                item = dict(record)
                item["text"] = identified[1]
                item["kind"] = "FULL"
                expanded.append(item)
                continue
            first = identify_text(lines[0])
            second = identify_text(lines[1])
            if first and second:
                kinds = {first[0], second[0]}
                if kinds == {"SIZE", "TYPE"}:
                    for ident, line in ((first, lines[0]), (second, lines[1])):
                        item = dict(record)
                        item["text"] = ident[1]
                        item["kind"] = ident[0]
                        expanded.append(item)
                    continue
            # Fall through and classify the whole block as one label.

        identified = identify_text(text) if text else None
        if identified is None and lines:
            identified = identify_text(" ".join(lines))
        if identified is None:
            continue

        if identified[0] == "PAIR":
            _, size, typ = identified
            for kind, value in (("SIZE", size), ("TYPE", typ)):
                item = dict(record)
                item["text"] = value
                item["kind"] = kind
                expanded.append(item)
            continue

        item = dict(record)
        item["text"] = identified[1]
        item["kind"] = identified[0]
        expanded.append(item)
    return expanded


def dedup_labels(labels, dist=DEDUP_DIST_MM):
    """Drop duplicate TEXT/MTEXT that come from block + modelspace scans."""
    kept = []
    for label in labels:
        duplicate = False
        for other in kept:
            if label["kind"] != other["kind"] or label["text"] != other["text"]:
                continue
            if hypot(label["x"] - other["x"], label["y"] - other["y"]) <= dist:
                duplicate = True
                break
        if not duplicate:
            kept.append(label)
    return kept


def hypot(dx, dy):
    return math.sqrt(dx * dx + dy * dy)


# ---------------------------------------------------------------------------
# SIZE + TYPE matching
# ---------------------------------------------------------------------------

def _nearest(item, candidates, max_dist, used):
    best_i = None
    best_dist = max_dist
    for i, other in enumerate(candidates):
        if i in used:
            continue
        dist = hypot(other["x"] - item["x"], other["y"] - item["y"])
        if dist < best_dist:
            best_dist = dist
            best_i = i
    if best_i is None:
        return None, None
    return best_i, best_dist


def match_size_type(labels):
    sizes = [lab for lab in labels if lab["kind"] == "SIZE"]
    types = [lab for lab in labels if lab["kind"] == "TYPE"]
    used_sizes = set()
    used_types = set()
    pairs = []

    def collect(max_dist, require_mutual=True):
        for si, size in enumerate(sizes):
            if si in used_sizes:
                continue
            ti, dist = _nearest(size, types, max_dist, used_types)
            if ti is None:
                continue
            if require_mutual:
                back, _ = _nearest(types[ti], sizes, max_dist, used_sizes)
                if back != si:
                    continue
            used_sizes.add(si)
            used_types.add(ti)
            pairs.append((size, types[ti], dist))

    collect(TIGHT_PAIR_DIST_MM, require_mutual=True)
    collect(LOOSE_PAIR_DIST_MM, require_mutual=True)
    collect(LOOSE_PAIR_DIST_MM, require_mutual=False)
    return pairs, used_sizes, used_types, sizes, types


def make_pair_gondola(size, typ, dist):
    dx = typ["x"] - size["x"]
    dy = typ["y"] - size["y"]
    # Label stack is usually perpendicular to the bay. Use that as a
    # fallback axis only after neighbour voting has had a chance.
    stack_angle = angle_from_offset(dx, dy)
    fallback_axis = normalize_line_angle(stack_angle + 90.0)
    text_rot = snap_line_angle(size.get("rotation", 0) or 0)
    x = (size["x"] + typ["x"]) / 2.0
    y = (size["y"] + typ["y"]) / 2.0
    code = size["text"] + typ["text"]
    if code not in FULL_CODES:
        joined = canonical_code(code)
        if joined in FULL_CODES:
            code = joined
    return {
        "code": code,
        "top": size["text"],
        "bottom": typ["text"],
        "x": round(x, 3),
        "y": round(y, 3),
        "rotation": round(float(size.get("rotation", 0) or 0), 3),
        "text_rotation": round(float(size.get("rotation", 0) or 0), 3),
        "orientation_angle": round(fallback_axis, 3),
        "revit_angle": round(tracing_to_revit_angle(fallback_axis), 3),
        "angle": round(tracing_to_revit_angle(fallback_axis), 3),
        "orientation": get_orientation(fallback_axis),
        "orientation_source": "PAIR_STACK_PERPENDICULAR",
        "pair_dx": round(dx, 1),
        "pair_dy": round(dy, 1),
        "pair_dist": round(dist, 1),
        "layer": size.get("layer", ""),
        "detection": "SIZE_TYPE",
        "text_rotation_snapped": text_rot,
        "_fallback_axis": fallback_axis,
    }


def make_full_gondola(label):
    text_rot = normalize_line_angle(label.get("rotation", 0) or 0)
    # Upright text (0°) is not a reliable axis. Keep it only as a hint.
    axis = snap_line_angle(text_rot) if angular_delta(text_rot, 0.0) > 8.0 else 0.0
    source = "TEXT_ROTATION" if angular_delta(text_rot, 0.0) > 8.0 else "DEFAULT_HORIZONTAL"
    return {
        "code": label["text"],
        "top": "",
        "bottom": "",
        "x": round(label["x"], 3),
        "y": round(label["y"], 3),
        "rotation": round(float(label.get("rotation", 0) or 0), 3),
        "text_rotation": round(float(label.get("rotation", 0) or 0), 3),
        "orientation_angle": round(axis, 3),
        "revit_angle": round(tracing_to_revit_angle(axis), 3),
        "angle": round(tracing_to_revit_angle(axis), 3),
        "orientation": get_orientation(axis),
        "orientation_source": source,
        "pair_dx": 0,
        "pair_dy": 0,
        "pair_dist": 0,
        "layer": label.get("layer", ""),
        "detection": "FULL_CODE",
        "text_rotation_snapped": snap_line_angle(text_rot),
        "_fallback_axis": axis,
    }


# ---------------------------------------------------------------------------
# Neighbour-run orientation
# ---------------------------------------------------------------------------

def _is_bay_spacing(dist):
    if dist < 400.0 or dist > NEIGHBOR_SEARCH_MM:
        return False
    for spacing in BAY_SPACINGS_MM:
        if abs(dist - spacing) <= BAY_SPACING_TOLERANCE_MM:
            return True
        if abs(dist - 2.0 * spacing) <= BAY_SPACING_TOLERANCE_MM:
            return True
    return False


def infer_run_angle(index, gondolas):
    """Vote on long-axis direction from neighbouring bay centres."""
    target = gondolas[index]
    votes = []
    for j, other in enumerate(gondolas):
        if j == index:
            continue
        dx = other["x"] - target["x"]
        dy = other["y"] - target["y"]
        dist = hypot(dx, dy)
        if not _is_bay_spacing(dist):
            continue
        weight = 2.0 if other["code"][:3] == target["code"][:3] else 1.0
        if other["code"] == target["code"]:
            weight += 1.5
        votes.append((weight, angle_from_offset(dx, dy), dist))

    if not votes:
        return None, None

    # Cluster votes that agree within 15°.
    buckets = []
    for weight, ang, dist in votes:
        placed = False
        for bucket in buckets:
            if angular_delta(bucket["angle"], ang) <= 15.0:
                bucket["weight"] += weight
                bucket["angles"].append(ang)
                placed = True
                break
        if not placed:
            buckets.append({"angle": ang, "weight": weight, "angles": [ang]})

    buckets.sort(key=lambda b: b["weight"], reverse=True)
    best = buckets[0]
    if best["weight"] < 1.0:
        return None, None
    mean = mean_line_angle(best["angles"])
    return snap_line_angle(mean), "NEIGHBOR_RUN"


def mean_line_angle(angles):
    """Circular mean of undirected line angles."""
    if not angles:
        return 0.0
    x = sum(math.cos(math.radians(2.0 * ang)) for ang in angles)
    y = sum(math.sin(math.radians(2.0 * ang)) for ang in angles)
    return normalize_line_angle(math.degrees(math.atan2(y, x)) / 2.0)


def apply_orientations(gondolas):
    """
    Fill orientation from neighbour runs, then inherit, then fallbacks.
    """
    resolved = [None] * len(gondolas)

    for i in range(len(gondolas)):
        angle, source = infer_run_angle(i, gondolas)
        if angle is not None:
            resolved[i] = (angle, source)

    # Isolated gondolas inherit from a nearby already-resolved neighbour.
    for i, gondola in enumerate(gondolas):
        if resolved[i] is not None:
            continue
        best = None
        best_dist = INHERIT_ORIENT_DIST_MM
        for j, other in enumerate(gondolas):
            if resolved[j] is None:
                continue
            dist = hypot(other["x"] - gondola["x"], other["y"] - gondola["y"])
            if dist < best_dist:
                best_dist = dist
                best = resolved[j]
        if best is not None:
            resolved[i] = (best[0], "INHERITED_NEIGHBOR")

    for i, gondola in enumerate(gondolas):
        if resolved[i] is None:
            text_rot = gondola.get("text_rotation_snapped", 0.0)
            if angular_delta(text_rot, 0.0) > 8.0:
                resolved[i] = (text_rot, "TEXT_ROTATION")
            else:
                resolved[i] = (
                    snap_line_angle(gondola.get("_fallback_axis", 0.0)),
                    gondola.get("orientation_source", "DEFAULT_HORIZONTAL"),
                )

        angle, source = resolved[i]
        angle = snap_line_angle(angle)
        gondola["orientation_angle"] = round(angle, 3)
        gondola["revit_angle"] = round(tracing_to_revit_angle(angle), 3)
        gondola["angle"] = gondola["revit_angle"]
        gondola["orientation"] = get_orientation(angle)
        gondola["orientation_source"] = source
        gondola.pop("_fallback_axis", None)
        gondola.pop("text_rotation_snapped", None)

    return gondolas


def _same_fixture(left, right):
    return compact_code(left.get("code", "")) == compact_code(right.get("code", ""))


def detection_rank(gondola):
    # Existing drawings use stacked SIZE+TYPE. Proposed drawings use
    # a single complete code. Prefer the pair when both sit on one bay.
    return 0 if gondola.get("detection") == "SIZE_TYPE" else 1


def dedup_overlapping_gondolas(gondolas, dist=OVERLAP_DEDUP_MM):
    """
    Drop a second family when existing and proposed labels name the
    same fixture in the same bay. Keep end panels next to gondolas.
    """
    ordered = sorted(
        gondolas,
        key=lambda item: (detection_rank(item), item.get("x", 0), item.get("y", 0)),
    )
    kept = []
    dropped = 0
    for item in ordered:
        clash = False
        for other in kept:
            if hypot(item["x"] - other["x"], item["y"] - other["y"]) > dist:
                continue
            if _same_fixture(item, other):
                clash = True
                break
        if clash:
            dropped += 1
            continue
        kept.append(item)
    return kept, dropped


def build_gondolas(raw_labels):
    """
    Full detector pipeline from raw DXF-like labels.

    Returns (gondolas, diagnostics).
    """
    filtered, layer_info = filter_proposed_layers(raw_labels)
    merged = merge_nearby_phrases(filtered)
    expanded = expand_raw_labels(merged)
    expanded = dedup_labels(expanded)

    pairs, used_sizes, used_types, sizes, types = match_size_type(expanded)
    gondolas = [make_pair_gondola(size, typ, dist) for size, typ, dist in pairs]

    for label in expanded:
        if label["kind"] == "FULL":
            gondolas.append(make_full_gondola(label))

    gondolas, dropped_overlaps = dedup_overlapping_gondolas(gondolas)
    gondolas = apply_orientations(gondolas)

    unmatched_sizes = [
        sizes[i] for i in range(len(sizes)) if i not in used_sizes
    ]
    unmatched_types = [
        types[i] for i in range(len(types)) if i not in used_types
    ]

    diagnostics = {
        "raw_labels": len(raw_labels),
        "classified_labels": len(expanded),
        "size_labels": len(sizes),
        "type_labels": len(types),
        "full_codes": sum(1 for lab in expanded if lab["kind"] == "FULL"),
        "pairs": len(pairs),
        "unmatched_sizes": unmatched_sizes,
        "unmatched_types": unmatched_types,
        "dropped_proposed_layer": layer_info["dropped_proposed_layer"],
        "dropped_overlaps": dropped_overlaps,
        "ignored_notes": sum(
            1 for label in raw_labels if is_noise_label(label.get("text", ""))
        ),
        "total": len(gondolas),
    }
    return gondolas, diagnostics


def summarise(gondolas):
    groups = defaultdict(list)
    for gondola in gondolas:
        groups[gondola["orientation"]].append(gondola)
    return {
        "total": len(gondolas),
        "horizontal": len(groups["HORIZONTAL"]),
        "vertical": len(groups["VERTICAL"]),
        "diagonal": len(groups["DIAGONAL"]),
        "groups": groups,
    }
