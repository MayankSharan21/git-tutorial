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
| Dynamo `Total JSON items : 0` | Detector skipped leftover blocks after seeing title text, and skipped the Selling-floor XREF that actually holds the store codes |
| V3 PDF: small inset families, gaps, worse than first run | Detector mixed leftover LOCAL SIZE+TYPE with XREF world coordinates, then Dynamo read an older New3 JSON |
| V4 PDF: coverage good, families beside their bays and some runs 90° out | Position came from the SIZE label, pairing reached into the next bay at 1500 mm, and rotation about the insertion point moved each body off its bay |
| V5 PDF: right size, 117 of 254 bays 90° out, centres ~18 pt off | Orientation came from voting on neighbouring label positions. An aisle has the same 1200 mm spacing as a run, so the vote cannot tell a run from the gap beside it |
| V6 PDF: identical to V5 (119 of 258 bays 90° out) | The bay-rectangle fit found no geometry and fell back to voting without saying so. It needed one rectangle per bay, searched by edge *midpoint*, and never looked inside nested blocks — so a run drawn as one long outline inside a block was invisible |

## What the new detector does

- Cleans MTEXT formatting and split labels (`15F` + `MCA`, `15F\PMCA`).
- Uses the original File1 collector: leftover named blocks + modelspace TEXT. Dynamo always adds the CAD offset. Orientation is rewritten afterwards from neighbour-run voting; DXF text rotation is ignored.
- Pairs SIZE+TYPE mutual-nearest (800 mm, then 1500 mm, then a greedy pass). Greedy 1500 mm alone let a SIZE grab the next bay's TYPE and dropped a family in the aisle.
- Writes the family position at the **bay centre** (midpoint of the two label lines), not at the SIZE label.
- **Reads the bay from the gondola drawn in the CAD**, because label positions alone cannot tell a run from the aisle beside it and the drawn outline can. Three tiers, best first, all of them CAD truth that neighbour voting may not override:
  - `CAD_RECTANGLE` — long sides and both ends found. Exact centre, axis and `bay_length` / `bay_depth`.
  - `CAD_DEPTH` — long sides only, which is what a run drawn as one long outline gives. Exact axis, exact centre across the bay, label position along it.
  - `CAD_EDGE` — direction only. Nothing is moved.
- To find that geometry it explodes nested blocks, measures distance to the whole edge rather than to its midpoint, keeps edges up to 40 m, and treats inner parallel lines as shelves across the bay but as bay divisions along it.
- Of the two directions a cell could run, it takes the one whose sides **run further**. The sides of a run are drawn as one line past every bay; the divisions between bays are a single bay long. Picking the narrower way across instead is what turned a 1200 wide by 1500 deep run 90°.
- `bay_length` is measured along the axis and `bay_depth` across it, as drawn. They are not sorted, because a run can be deeper than it is long.
- If the labels are in a block and the outlines in modelspace, their coordinates look unrelated. The detector uses the block's own INSERT as the exact transform between the two rather than guessing an offset, and says so when it does.
- Dynamo measures each placed footprint and turns it onto the bay axis about the footprint centre, then centres it on the bay. Rotating about the insertion point swung bodies off their bays, because these families are not centred on their origin.
- Matches SIZE+TYPE with mutual nearest-neighbour and a ~700 mm stack window so adjacent 1200 mm bays are not paired.
- Infers orientation from neighbouring bay centres (1200 / 1500 / 1800 mm runs). This is what aligns the Marrickville south wall, west wall, and 45° corner.
- Writes three angle fields:
  - `orientation_angle` — long axis, 0 = +X, 90 = +Y
  - `revit_angle` / `angle` — family rotation (horizontal = 90, vertical = 0)

## What the new Dynamo script does

- Uses `revit_angle` / `angle` / `orientation_angle` only. Ignores text `rotation`.
- Chooses the quarter turn whose resulting extents match `bay_length` / `bay_depth`, so a family whose bounding box is bigger than its footprint still lands along the bay. `bay_depth` on its own is enough. The report shows `Angle read from CAD: N of M` and a per-item `fit=(+dx,+dy) mm`, which is where a wrong family size shows up.
- Looks up TYPE_MAP case-insensitively (`6WAY` works).
- Falls back to loaded End_Panel types when `End_Panel_Decks` types are missing.
- `EXISTING_ONLY = True`: refuses Proposed levels, overlay views, and the selling-floor CAD. Places only on Existing.
- Prefers the CAD link whose name contains “Existing Conditions”.
- If the JSON is empty, Dynamo reports the file size and keys and does **not** delete already-placed families.
- Places on the **Existing Conditions view’s associated level**, not blindly on `00-GROUND`. Floor plans only show families hosted on their own level.

## How to run

1. Replace **both** files. Dynamo must report `2026-10-05s-run-axis`. Re-run the detector (leftover named blocks, mutual-nearest pairing, XY = bay centre) so it writes `gondola_data_Marrickville_New4.json`, then run Dynamo. Do not reuse New2 / New3.
2. Copy only `Gondola_OrientationDetector.py` into the Tracing folder. It is standalone — an old `gondola_lib.py` in that folder is ignored.
3. Edit `DXF_FILE_PATH` and `OUTPUT_JSON` at the top of `Gondola_OrientationDetector.py`. Use the Existing Conditions GROUND DXF.
4. `pip install ezdxf` if needed, then run the detector.
5. Confirm the report: `Total gondolas` must not be 0, and `No CAD outline near` should be close to 0. Anything counted there falls back to `NEIGHBOR_RUN` voting, which is what put half the V5 / V6 bays 90° out. If that count is high, compare the printed outline and gondola coordinate ranges — different ranges mean the labels and the geometry are in different DXF spaces.
6. Paste `Dynamo_ExistingGondolaPlacement.py` into Dynamo. Set `JSON_PATH` to the same file the detector just wrote. Set `LEVEL_NAME` if this store uses different names.
7. Leave `EXISTING_ONLY = True`. The script refuses Proposed levels, overlay views, and the selling-floor CAD link.
8. Run once. The script deletes previously managed gondolas on that Existing level / Existing phase before placing — unless the JSON is empty, in which case it deletes nothing.

## Tests

```bash
python -m unittest gondola_tracing.tests.test_gondola_tracing
```

The tests rebuild the Marrickville wall runs from the 5 Oct coordinates and assert the corrected angles without needing the DXF or Revit.
