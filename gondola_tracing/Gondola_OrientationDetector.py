# Gondola_OrientationDetector.py
#
# Run this from a VS Code / system Python terminal (not Dynamo).
#
# Reads gondola labels from a DXF, matches SIZE + TYPE pairs, infers the
# physical bay run direction, and writes JSON for
# Dynamo_ExistingGondolaPlacement.py.
#
# orientation_angle = gondola long axis in DXF degrees (0 = +X, 90 = +Y)
# revit_angle / angle = family rotation to apply in Revit
#     HORIZONTAL -> 90
#     VERTICAL   -> 0

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

import json
import os
import sys

import ezdxf

try:
    from gondola_lib import build_gondolas, is_proposed_scope, summarise
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from gondola_lib import build_gondolas, is_proposed_scope, summarise


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


DXF_FILE_PATH = r"C:\Users\msharan\OneDrive - Kmart Australia Limited\Desktop\Stores Foundry\PPT , Requirements, Demo videos, Pics\1131 Marrickville-Existing plan trace exercise_2 - Floor Plan - 1-0 EXISTING CONDITIONS - GROUND.dxf"

OUTPUT_JSON = r"C:\Users\msharan\OneDrive - Kmart Australia Limited\Desktop\Stores Foundry\Tracing\json\gondola_data_Marrickville_New2.json"

# Never explode proposed / selling-floor XREFs or leftover proposed blocks.
EXISTING_ONLY = True


def _entity_point(entity):
    try:
        insert = entity.dxf.insert
        return float(insert.x), float(insert.y)
    except Exception:
        return None


def _entity_rotation(entity):
    try:
        return float(entity.dxf.get("rotation", 0) or 0)
    except Exception:
        return 0.0


def _entity_layer(entity):
    try:
        return entity.dxf.layer or ""
    except Exception:
        return ""


def _entity_text(entity):
    dxftype = entity.dxftype()
    try:
        if dxftype == "MTEXT":
            return entity.text
        return entity.dxf.text
    except Exception:
        return ""


def _as_label(entity):
    point = _entity_point(entity)
    if point is None:
        return None
    text = _entity_text(entity)
    if not text:
        return None
    return {
        "text": text,
        "x": point[0],
        "y": point[1],
        "rotation": _entity_rotation(entity),
        "layer": _entity_layer(entity),
    }


def _walk_insert(entity, collector, depth=0):
    if depth > 8:
        return
    try:
        virtuals = list(entity.virtual_entities())
    except Exception:
        virtuals = []
        try:
            block = entity.doc.blocks.get(entity.dxf.name)
        except Exception:
            block = None
        if block is None:
            return
        for child in block:
            _collect_entity(child, collector, depth + 1)
        return

    for child in virtuals:
        _collect_entity(child, collector, depth + 1)


def _collect_entity(entity, collector, depth=0):
    try:
        dxftype = entity.dxftype()
    except Exception:
        return

    if dxftype in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF"):
        label = _as_label(entity)
        if label is not None:
            collector.append(label)
        return

    if dxftype == "INSERT":
        try:
            block_name = entity.dxf.name
        except Exception:
            block_name = ""
        if EXISTING_ONLY and is_proposed_scope(block_name):
            return
        _walk_insert(entity, collector, depth)


def collect_dxf_labels(dxf_path):
    print("Loading DXF file...")
    print(dxf_path)
    print("")

    doc = ezdxf.readfile(dxf_path)
    print("DXF loaded!")
    if EXISTING_ONLY and is_proposed_scope(dxf_path):
        print("WARNING: DXF path looks like a Proposed / selling-floor file.")
        print("Tracing must use the Existing Conditions drawing only.")
        print("")
    print("")

    labels = []

    print("Scanning modelspace (including INSERTs / XREFs)...")
    for entity in doc.modelspace():
        try:
            _collect_entity(entity, labels)
        except Exception:
            pass

    # Only scan leftover block definitions when modelspace was empty.
    # Overlay DXFs often keep the proposed selling-floor labels in a
    # second block. Reading both stacks two families on every bay.
    extra = []
    if not labels:
        print("Modelspace had no labels. Scanning leftover block definitions...")
        seen = set()
        for block_def in doc.blocks:
            try:
                name = block_def.name
            except Exception:
                continue
            if name.startswith("*"):
                continue
            if EXISTING_ONLY and is_proposed_scope(name):
                continue
            for entity in block_def:
                try:
                    if entity.dxftype() not in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF"):
                        continue
                    label = _as_label(entity)
                    if label is None:
                        continue
                    key = (round(label["x"], 1), round(label["y"], 1), label["text"])
                    if key in seen:
                        continue
                    extra.append(label)
                    seen.add(key)
                except Exception:
                    pass
        labels.extend(extra)
    else:
        print("Skipping leftover block definitions (modelspace already has labels).")

    print("Labels collected: {}".format(len(labels)))
    print("")
    return labels


def extract_with_orientation(dxf_path):
    labels = collect_dxf_labels(dxf_path)
    gondolas, diagnostics = build_gondolas(labels)

    print("Classified labels : {}".format(diagnostics["classified_labels"]))
    print("Size labels found : {}".format(diagnostics["size_labels"]))
    print("Type labels found : {}".format(diagnostics["type_labels"]))
    print("Complete codes    : {}".format(diagnostics["full_codes"]))
    print("SIZE+TYPE pairs   : {}".format(diagnostics["pairs"]))
    print("Unmatched sizes   : {}".format(len(diagnostics["unmatched_sizes"])))
    print("Unmatched types   : {}".format(len(diagnostics["unmatched_types"])))
    print("Ignored notes     : {}".format(diagnostics.get("ignored_notes", 0)))
    print("Dropped proposed  : {}".format(diagnostics.get("dropped_proposed_layer", 0)))
    print("Dropped overlaps  : {}".format(diagnostics.get("dropped_overlaps", 0)))
    print("")
    return gondolas, diagnostics


def print_report(gondolas, diagnostics):
    stats = summarise(gondolas)
    total = stats["total"]

    print("")
    print("=" * 60)
    print("  GONDOLA ORIENTATION REPORT")
    print("=" * 60)
    print("")
    print("Total gondolas : {}".format(total))
    print("Horizontal     : {} ({:.1f}%)".format(
        stats["horizontal"],
        stats["horizontal"] / total * 100 if total else 0,
    ))
    print("Vertical       : {} ({:.1f}%)".format(
        stats["vertical"],
        stats["vertical"] / total * 100 if total else 0,
    ))
    print("Diagonal       : {} ({:.1f}%)".format(
        stats["diagonal"],
        stats["diagonal"] / total * 100 if total else 0,
    ))
    print("")

    for label, key, arrow in (
        ("HORIZONTAL", "HORIZONTAL", "→"),
        ("VERTICAL", "VERTICAL", "↑"),
        ("DIAGONAL", "DIAGONAL", "↗"),
    ):
        group = stats["groups"][key]
        print("─" * 60)
        print("{} GONDOLAS ({}):".format(label, arrow))
        print("─" * 60)
        for gondola in group:
            print(
                "  {:<30} "
                "x={:>8.0f} "
                "y={:>8.0f} "
                "axis={:>7.2f}° "
                "revit={:>7.2f}° "
                "dist={:>7.1f}mm "
                "[{} / {}]".format(
                    gondola["code"],
                    gondola["x"],
                    gondola["y"],
                    gondola.get("orientation_angle", 0),
                    gondola.get("revit_angle", 0),
                    gondola["pair_dist"],
                    gondola["detection"],
                    gondola.get("orientation_source", ""),
                )
            )
        print("")

    from collections import defaultdict
    breakdown = defaultdict(lambda: {"H": 0, "V": 0, "D": 0, "total": 0})
    for gondola in gondolas:
        name = gondola["code"]
        ori = gondola["orientation"][0]
        breakdown[name][ori] += 1
        breakdown[name]["total"] += 1

    print("─" * 60)
    print("COUNT BY CODE:")
    print("─" * 60)
    print("{:<30} {:>6} {:>6} {:>6} {:>6}".format("Code", "Total", "H", "V", "D"))
    print("─" * 58)
    for name in sorted(breakdown):
        row = breakdown[name]
        print("{:<30} {:>6} {:>6} {:>6} {:>6}".format(
            name, row["total"], row["H"], row["V"], row["D"]
        ))

    if diagnostics["unmatched_sizes"] or diagnostics["unmatched_types"]:
        print("")
        print("─" * 60)
        print("UNMATCHED LABELS (not placed):")
        print("─" * 60)
        for label in diagnostics["unmatched_sizes"]:
            print("  SIZE {:<12} x={:.0f} y={:.0f}".format(
                label["text"], label["x"], label["y"]
            ))
        for label in diagnostics["unmatched_types"]:
            print("  TYPE {:<12} x={:.0f} y={:.0f}".format(
                label["text"], label["x"], label["y"]
            ))


def save_json(path, gondolas):
    stats = summarise(gondolas)
    payload = {
        "total": stats["total"],
        "horizontal": stats["horizontal"],
        "vertical": stats["vertical"],
        "diagonal": stats["diagonal"],
        "gondolas": gondolas,
    }
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print("")
    print("Saved to:")
    print(path)


def main():
    print("")
    print("=" * 60)
    print("  GONDOLA ORIENTATION DETECTOR")
    print("=" * 60)
    print("")

    gondolas, diagnostics = extract_with_orientation(DXF_FILE_PATH)
    print_report(gondolas, diagnostics)
    save_json(OUTPUT_JSON, gondolas)

    print("")
    print("=" * 60)
    print("  COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
