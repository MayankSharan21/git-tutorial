# Gondola tracing

Two-step workflow that traces existing-condition gondolas from a store DXF into Revit 2025.

1. `Gondola_OrientationDetector.py` — run in a VS Code / system Python terminal.
2. `Dynamo_ExistingGondolaPlacement.py` — paste into a Dynamo Python node and run inside Revit.

## Why the overlay looks like it “does not understand” the plan

The 5 Oct Marrickville PDF is an **existing + proposed overlay**, not a single label set. The tracer was reading both, then Dynamo painted the result onto `5.0 OVERLAY- EXISTING & PROPOSED PLAN`. That is the “lot of overriding”:

1. **Two complete plans in one drawing.** Existing bays are labelled `15F` + `MCA` (and old codes such as `15SHMC`). The proposed selling floor repeats the same bays as complete codes (`15FMCA`, `36WLOA`, `LRD`). Placing both puts two families on one bay.
2. **Notes are not fixtures.** `DE`, `RD`, `390`, `2x(595x1195)`, `(VM)`, `NO EPF`, `CLADDED SURROUND` sit next to real codes. Treating them as gondolas fills gaps with junk.
3. **Split words.** `STRAIGHT` / `RAIL`, `FLATDECK` / `W/-SURROUND`, `HOPPER` / `UNIT 2150H` were not joined, so those fixtures were skipped.
4. **Graphic override on the overlay view.** The previous run targeted the overlay view and the proposed level, so existing-phase families sat on top of proposed families and turned blue.

Run the detector on the **Existing Conditions** DXF only, and run Dynamo on an existing-only view — not the overlay.

## What was wrong on Marrickville

The 5 Oct 2026 run placed **1526 / 1593** items and every family landed at **0°**.

| Symptom | Cause |
| --- | --- |
| Every gondola at 0° | Dynamo read DXF text `rotation` (almost always 0) before `orientation_angle` |
| Horizontal and vertical runs swapped | SIZE+TYPE stack was treated as the bay axis. Labels sit *across* the bay, so a south-wall run voted vertical |
| 135° walls called vertical | Any angle above 65° was classified vertical |
| `6WAY` skipped | Detector uppercased the code; TYPE_MAP key was `6Way` |
| Deck / hotspot items skipped | Preferred Revit types were not loaded and there was no fallback |

## What the new detector does

- Cleans MTEXT formatting and split labels (`15F` + `MCA`, `15F\PMCA`).
- Walks modelspace INSERTs / XREFs instead of raw block-definition coordinates.
- Matches SIZE+TYPE with mutual nearest-neighbour and a ~700 mm stack window so adjacent 1200 mm bays are not paired.
- Infers orientation from neighbouring bay centres (1200 / 1500 / 1800 mm runs). This is what aligns the Marrickville south wall, west wall, and 45° corner.
- Writes three angle fields:
  - `orientation_angle` — long axis, 0 = +X, 90 = +Y
  - `revit_angle` / `angle` — family rotation (horizontal = 90, vertical = 0)

## What the new Dynamo script does

- Uses `revit_angle` / `angle` / `orientation_angle` only. Ignores text `rotation`.
- Looks up TYPE_MAP case-insensitively (`6WAY` works).
- Falls back to loaded End_Panel types when `End_Panel_Decks` types are missing.
- `EXISTING_ONLY = True`: refuses Proposed levels, overlay views, and the selling-floor CAD. Places only on Existing.
- Prefers the CAD link whose name contains “Existing Conditions”.

## How to run

1. Edit `DXF_FILE_PATH` and `OUTPUT_JSON` at the top of `Gondola_OrientationDetector.py`.
2. `pip install ezdxf` if needed, then run the detector.
3. Confirm the report: unmatched SIZE/TYPE lines should be near zero, and wall runs should show `NEIGHBOR_RUN` with 0° / 90° / 45° / 135° axes.
4. Paste `Dynamo_ExistingGondolaPlacement.py` into Dynamo. Set `JSON_PATH` and `LEVEL_NAME` if this store uses different names.
5. Leave `EXISTING_ONLY = True`. The script refuses Proposed levels, overlay views, and the selling-floor CAD link.
6. Run once. The script deletes previously managed gondolas on that Existing level / Existing phase before placing.

## Tests

```bash
python -m unittest gondola_tracing.tests.test_gondola_tracing
```

The tests rebuild the Marrickville wall runs from the 5 Oct coordinates and assert the corrected angles without needing the DXF or Revit.
