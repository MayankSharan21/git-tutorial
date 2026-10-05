# Gondola_OrientationDetector.py
#
# Run in VS Code / any Python 3 terminal (needs ezdxf).
#
# Reads gondola labels from a DXF, pairs SIZE+TYPE, reads nearby CAD
# strokes for the true bay axis, and writes JSON for the Dynamo
# Revit 2025 placement script.
#
# Keep this file next to gondola_tracing_lib.py and gondola_codes.py.

from __future__ import annotations

import json
import math
import os
import platform as _platform
import sys
from collections import defaultdict

if not hasattr(_platform, "_patched"):
    _orig = _platform._syscmd_ver

    def _safe_syscmd_ver(*a, **kw):
        try:
            return _orig(*a, **kw)
        except Exception:
            return ("", "", "", "")

    _platform._syscmd_ver = _safe_syscmd_ver
    _platform._patched = True

import ezdxf

from gondola_codes import FULL_CODES, SIZE_CODES, TYPE_CODES
from gondola_tracing_lib import (
    estimate_gondola_axis,
    insunits_to_mm,
    match_size_type_pairs,
    normalize_angle_360,
    normalize_code,
    snap_axis_angle,
    smooth_run_orientations,
    text_visual_point,
)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


DXF_FILE_PATH = r"C:\Users\msharan\OneDrive - Kmart Australia Limited\Desktop\Stores Foundry\PPT , Requirements, Demo videos, Pics\1131 Marrickville-Existing plan trace exercise_2 - Floor Plan - 1-0 EXISTING CONDITIONS - GROUND.dxf"

OUTPUT_JSON = r"C:\Users\msharan\OneDrive - Kmart Australia Limited\Desktop\Stores Foundry\Tracing\json\gondola_data_Marrickville_New2.json"


def _unit_scale(doc) -> float:
    try:
        insunits = int(doc.header.get("$INSUNITS", 0) or 0)
    except Exception:
        insunits = 0
    return insunits_to_mm(insunits)


def _entity_text(entity) -> str:
    dxftype = entity.dxftype()
    if dxftype == "MTEXT":
        try:
            raw = entity.plain_text()
        except Exception:
            raw = getattr(entity, "text", "") or entity.dxf.get("text", "")
        return normalize_code(raw)
    if dxftype == "TEXT":
        return normalize_code(entity.dxf.get("text", ""))
    if dxftype == "ATTRIB":
        return normalize_code(entity.dxf.get("text", ""))
    return ""


def _entity_xy_rotation(entity, scale: float):
    try:
        insert = entity.dxf.insert
        x, y = float(insert.x), float(insert.y)
    except Exception:
        return None

    rotation = 0.0
    try:
        rotation = float(entity.dxf.get("rotation", 0) or 0)
    except Exception:
        rotation = 0.0

    height = 0.0
    try:
        if entity.dxftype() == "MTEXT":
            height = float(entity.dxf.get("char_height", 0) or 0)
        else:
            height = float(entity.dxf.get("height", 0) or 0)
    except Exception:
        height = 0.0

    halign = 0
    valign = 0
    width_factor = 1.0
    align_x = None
    align_y = None
    try:
        halign = int(entity.dxf.get("halign", 0) or 0)
        valign = int(entity.dxf.get("valign", 0) or 0)
        width_factor = float(entity.dxf.get("width", 1) or 1)
    except Exception:
        pass
    try:
        align = entity.dxf.get("align_point")
        if align is not None:
            align_x, align_y = float(align.x), float(align.y)
    except Exception:
        pass

    text = _entity_text(entity)
    vx, vy = text_visual_point(
        x,
        y,
        rotation,
        height,
        text,
        halign=halign,
        valign=valign,
        width_factor=width_factor,
        align_x=align_x,
        align_y=align_y,
    )
    return vx * scale, vy * scale, rotation, (height or 0.0) * scale, text


def _layer_name(entity) -> str:
    try:
        return str(entity.dxf.layer or "")
    except Exception:
        return ""


def _collect_segments_from_entity(entity, scale: float, out: list) -> None:
    dt = entity.dxftype()
    try:
        if dt == "LINE":
            s = entity.dxf.start
            e = entity.dxf.end
            out.append((s.x * scale, s.y * scale, e.x * scale, e.y * scale))
        elif dt == "LWPOLYLINE":
            pts = list(entity.get_points("xy"))
            closed = bool(entity.closed)
            for i in range(len(pts) - 1):
                x1, y1 = pts[i][0], pts[i][1]
                x2, y2 = pts[i + 1][0], pts[i + 1][1]
                out.append((x1 * scale, y1 * scale, x2 * scale, y2 * scale))
            if closed and len(pts) > 2:
                x1, y1 = pts[-1][0], pts[-1][1]
                x2, y2 = pts[0][0], pts[0][1]
                out.append((x1 * scale, y1 * scale, x2 * scale, y2 * scale))
        elif dt == "POLYLINE":
            pts = []
            for v in entity.vertices:
                try:
                    loc = v.dxf.location
                    pts.append((loc.x, loc.y))
                except Exception:
                    continue
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i + 1]
                out.append((x1 * scale, y1 * scale, x2 * scale, y2 * scale))
        elif dt == "ARC":
            # Approximate the chord; useful for curved hotspot rails.
            c = entity.dxf.center
            r = float(entity.dxf.radius)
            a0 = math.radians(float(entity.dxf.start_angle))
            a1 = math.radians(float(entity.dxf.end_angle))
            x1 = (c.x + r * math.cos(a0)) * scale
            y1 = (c.y + r * math.sin(a0)) * scale
            x2 = (c.x + r * math.cos(a1)) * scale
            y2 = (c.y + r * math.sin(a1)) * scale
            out.append((x1, y1, x2, y2))
    except Exception:
        return


def _walk_entity(entity):
    dt = entity.dxftype()
    if dt == "INSERT":
        try:
            for attrib in entity.attribs:
                yield attrib
        except Exception:
            pass
        nested = []
        try:
            nested = list(entity.virtual_entities())
        except Exception:
            nested = []
        if not nested:
            yield entity
            return
        for ve in nested:
            for child in _walk_entity(ve):
                yield child
        return
    yield entity


def _iter_model_entities(doc):
    """
    Yield modelspace entities with INSERT exploded via virtual_entities,
    including nested blocks.
    """
    msp = doc.modelspace()
    for entity in msp:
        for child in _walk_entity(entity):
            yield child


def extract_with_orientation(dxf_path: str):
    size_texts = []
    type_texts = []
    full_code_gondolas = []
    segments = []

    print("Loading DXF file...")
    print(dxf_path)
    print("")

    doc = ezdxf.readfile(dxf_path)
    scale = _unit_scale(doc)
    print("DXF loaded. Unit scale to mm: {}".format(scale))
    print("")

    print("Scanning modelspace (INSERT-aware)...")
    for entity in _iter_model_entities(doc):
        try:
            _collect_segments_from_entity(entity, scale, segments)
        except Exception:
            pass

        dt = entity.dxftype()
        if dt not in ("TEXT", "MTEXT", "ATTRIB"):
            continue

        parsed = _entity_xy_rotation(entity, scale)
        if not parsed:
            continue
        x, y, rotation, height, text = parsed
        if not text:
            continue
        layer = _layer_name(entity)

        item = {
            "text": text,
            "x": round(x, 3),
            "y": round(y, 3),
            "rotation": round(rotation, 3),
            "label_rotation": round(normalize_angle_360(rotation), 3),
            "height": round(height, 3),
            "layer": layer,
        }

        if text in FULL_CODES:
            full_code_gondolas.append(item)
            continue
        if text in SIZE_CODES:
            size_texts.append(item)
        elif text in TYPE_CODES:
            type_texts.append(item)

    print("Size labels found: {}".format(len(size_texts)))
    print("Type labels found: {}".format(len(type_texts)))
    print("Complete codes found: {}".format(len(full_code_gondolas)))
    print("CAD segments cached: {}".format(len(segments)))
    print("")

    gondolas = []
    matches = match_size_type_pairs(size_texts, type_texts)
    used_size = {si for si, _ti, _d in matches}
    used_type = {ti for _si, ti, _d in matches}

    for si, ti, dist in matches:
        size_item = size_texts[si]
        type_item = type_texts[ti]
        sx, sy = size_item["x"], size_item["y"]
        tx, ty = type_item["x"], type_item["y"]
        dx, dy = tx - sx, ty - sy
        cx = (sx + tx) / 2.0
        cy = (sy + ty) / 2.0
        axis = estimate_gondola_axis(
            cx,
            cy,
            dx,
            dy,
            dist,
            size_item["label_rotation"],
            segments,
        )
        gondolas.append(
            {
                "code": size_item["text"] + type_item["text"],
                "top": size_item["text"],
                "bottom": type_item["text"],
                "x": round(cx, 3),
                "y": round(cy, 3),
                "label_x": round(sx, 3),
                "label_y": round(sy, 3),
                "rotation": axis["placement_angle"],
                "orientation_angle": axis["orientation_angle"],
                "placement_angle": axis["placement_angle"],
                "orientation": axis["orientation"],
                "pair_dx": round(dx, 1),
                "pair_dy": round(dy, 1),
                "pair_dist": round(dist, 1),
                "pair_angle": axis["pair_angle"],
                "geometry_angle": axis["geometry_angle"],
                "geometry_confidence": axis["geometry_confidence"],
                "axis_source": axis["axis_source"],
                "snap_source": axis["snap_source"],
                "label_rotation": axis["label_rotation"],
                "layer": size_item["layer"],
                "detection": "SIZE_TYPE",
            }
        )

    for item in full_code_gondolas:
        axis = estimate_gondola_axis(
            item["x"],
            item["y"],
            0.0,
            0.0,
            0.0,
            item["label_rotation"],
            segments,
        )
        snapped, snap_src = snap_axis_angle(axis["orientation_angle"])
        gondolas.append(
            {
                "code": item["text"],
                "top": "",
                "bottom": "",
                "x": item["x"],
                "y": item["y"],
                "label_x": item["x"],
                "label_y": item["y"],
                "rotation": axis["placement_angle"],
                "orientation_angle": round(snapped, 3),
                "placement_angle": axis["placement_angle"],
                "orientation": axis["orientation"],
                "pair_dx": 0,
                "pair_dy": 0,
                "pair_dist": 0,
                "pair_angle": 0,
                "geometry_angle": axis["geometry_angle"],
                "geometry_confidence": axis["geometry_confidence"],
                "axis_source": axis["axis_source"]
                if axis["geometry_angle"] is not None
                else "full_code_geometry_or_label",
                "snap_source": snap_src,
                "label_rotation": item["label_rotation"],
                "layer": item["layer"],
                "detection": "FULL_CODE",
            }
        )

    print(
        "Unmatched size labels: {}".format(len(size_texts) - len(used_size))
    )
    print(
        "Unmatched type labels: {}".format(len(type_texts) - len(used_type))
    )
    smoothed = smooth_run_orientations(gondolas)
    print("Run-consensus angle fixes: {}".format(smoothed))
    return gondolas, {
        "unmatched_size": [
            size_texts[i] for i in range(len(size_texts)) if i not in used_size
        ],
        "unmatched_type": [
            type_texts[i] for i in range(len(type_texts)) if i not in used_type
        ],
        "unit_scale_to_mm": scale,
        "segment_count": len(segments),
    }


def print_report(gondolas, extras):
    print("")
    print("=" * 60)
    print("  GONDOLA ORIENTATION REPORT")
    print("=" * 60)
    print("")

    horizontal = [g for g in gondolas if g["orientation"] == "HORIZONTAL"]
    vertical = [g for g in gondolas if g["orientation"] == "VERTICAL"]
    diagonal = [g for g in gondolas if g["orientation"] == "DIAGONAL"]
    total = len(gondolas)

    print("Total gondolas : {}".format(total))
    print(
        "Horizontal     : {} ({:.1f}%)".format(
            len(horizontal),
            len(horizontal) / total * 100 if total else 0,
        )
    )
    print(
        "Vertical       : {} ({:.1f}%)".format(
            len(vertical),
            len(vertical) / total * 100 if total else 0,
        )
    )
    print(
        "Diagonal       : {} ({:.1f}%)".format(
            len(diagonal),
            len(diagonal) / total * 100 if total else 0,
        )
    )
    print("")

    for label, group, arrow in (
        ("HORIZONTAL", horizontal, "→"),
        ("VERTICAL", vertical, "↑"),
        ("DIAGONAL", diagonal, "↗"),
    ):
        print("─" * 60)
        print("{} GONDOLAS ({}):".format(label, arrow))
        print("─" * 60)
        for g in group:
            print(
                "  {:<30} x={:>8.0f} y={:>8.0f} "
                "axis={:>7.2f}° place={:>7.2f}° dist={:>7.1f}mm "
                "[{} / {}]".format(
                    g["code"],
                    g["x"],
                    g["y"],
                    g.get("orientation_angle", 0),
                    g.get("placement_angle", 0),
                    g["pair_dist"],
                    g["detection"],
                    g.get("axis_source", ""),
                )
            )
        print("")

    print("─" * 60)
    print("COUNT BY CODE:")
    print("─" * 60)
    breakdown = defaultdict(lambda: {"H": 0, "V": 0, "D": 0, "total": 0})
    for g in gondolas:
        name = g["code"]
        ori = g["orientation"][0]
        breakdown[name][ori] += 1
        breakdown[name]["total"] += 1
    print("{:<30} {:>6} {:>6} {:>6} {:>6}".format("Code", "Total", "H", "V", "D"))
    print("─" * 58)
    for name in sorted(breakdown):
        b = breakdown[name]
        print(
            "{:<30} {:>6} {:>6} {:>6} {:>6}".format(
                name, b["total"], b["H"], b["V"], b["D"]
            )
        )

    unmatched_s = extras.get("unmatched_size") or []
    unmatched_t = extras.get("unmatched_type") or []
    if unmatched_s or unmatched_t:
        print("")
        print("─" * 60)
        print("UNMATCHED LABELS (check overlapping text / missing pair)")
        print("─" * 60)
        for item in unmatched_s:
            print(
                "  SIZE {:<8} x={:.0f} y={:.0f}".format(
                    item["text"], item["x"], item["y"]
                )
            )
        for item in unmatched_t:
            print(
                "  TYPE {:<8} x={:.0f} y={:.0f}".format(
                    item["text"], item["x"], item["y"]
                )
            )


def save_json(path, gondolas, extras):
    horizontal = [g for g in gondolas if g["orientation"] == "HORIZONTAL"]
    vertical = [g for g in gondolas if g["orientation"] == "VERTICAL"]
    diagonal = [g for g in gondolas if g["orientation"] == "DIAGONAL"]
    output = {
        "total": len(gondolas),
        "horizontal": len(horizontal),
        "vertical": len(vertical),
        "diagonal": len(diagonal),
        "unit_scale_to_mm": extras.get("unit_scale_to_mm"),
        "segment_count": extras.get("segment_count"),
        "unmatched_size_count": len(extras.get("unmatched_size") or []),
        "unmatched_type_count": len(extras.get("unmatched_type") or []),
        "gondolas": gondolas,
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, ensure_ascii=False)
    print("")
    print("Saved to:")
    print(path)


def main():
    print("")
    print("=" * 60)
    print("  GONDOLA ORIENTATION DETECTOR")
    print("=" * 60)
    print("")
    gondolas, extras = extract_with_orientation(DXF_FILE_PATH)
    print_report(gondolas, extras)
    save_json(OUTPUT_JSON, gondolas, extras)
    print("")
    print("=" * 60)
    print("  COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
