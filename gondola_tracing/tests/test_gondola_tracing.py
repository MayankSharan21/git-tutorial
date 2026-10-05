import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from gondola_lib import (
    apply_orientations,
    build_gondolas,
    canonical_code,
    choose_existing_level_name,
    choose_existing_placement,
    choose_existing_view_name,
    classify_revit_name,
    expand_raw_labels,
    get_orientation,
    has_classified_gondola,
    identify_text,
    is_existing_ground_view,
    is_existing_conditions_view,
    is_layout_block,
    is_noise_label,
    is_proposed_scope,
    keep_existing_source_labels,
    load_gondola_items,
    match_size_type,
    merge_nearby_phrases,
    normalize_line_angle,
    pick_json_angle,
    bay_alignment_delta,
    bay_axis_from_item,
    bay_dims_from_item,
    bay_rect_from_segments,
    compatible_leftover_labels,
    estimated_gondola_yield,
    fold_line_angle,
    footprint_alignment_delta,
    footprint_fit_error,
    pick_label_set,
    plan_extent,
    should_apply_cad_translation,
    should_scan_leftover,
    snap_line_angle,
    strip_mtext_codes,
    tracing_to_revit_angle,
)


class TextCleanupTests(unittest.TestCase):
    def test_strips_mtext_formatting(self):
        raw = r"{\fArial|b0|i0|c0|p34;15FMCA}"
        self.assertEqual(strip_mtext_codes(raw).replace(" ", ""), "15FMCA")

    def test_splits_paragraph_into_size_type(self):
        labels = expand_raw_labels([
            {"text": "15F\\PMCA", "x": 100, "y": 200, "rotation": 0, "layer": "A"}
        ])
        kinds = sorted(item["kind"] for item in labels)
        self.assertIn(kinds, (["FULL"], ["SIZE", "TYPE"]))
        if kinds == ["FULL"]:
            self.assertEqual(labels[0]["text"], "15FMCA")
        else:
            texts = {item["kind"]: item["text"] for item in labels}
            self.assertEqual(texts["SIZE"], "15F")
            self.assertEqual(texts["TYPE"], "MCA")

    def test_aliases_six_way(self):
        self.assertEqual(canonical_code("6Way"), "6WAY")
        self.assertEqual(canonical_code("6 WAY"), "6WAY")
        self.assertEqual(identify_text("6Way")[1], "6WAY")

    def test_identifies_old_end_panel(self):
        self.assertEqual(identify_text("15EPLC"), ("FULL", "15EPLC"))

    def test_identifies_spaced_pair(self):
        # Known combinations collapse to the catalogue code.
        self.assertEqual(identify_text("15F MCA"), ("FULL", "15FMCA"))

    def test_ignores_overlay_notes(self):
        for note in ("DE", "RD", "390", "2x(595x1195)", "(VM)", "NO EPF"):
            self.assertTrue(is_noise_label(note), note)
            self.assertIsNone(identify_text(note))

    def test_joins_straight_rail(self):
        merged = merge_nearby_phrases([
            {"text": "STRAIGHT", "x": 0, "y": 0, "rotation": 0},
            {"text": "RAIL", "x": 80, "y": 20, "rotation": 0},
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual(canonical_code(merged[0]["text"]), "STRAIGHT RAIL")


class ExistingOnlyScopeTests(unittest.TestCase):
    def test_classifies_marrickville_names(self):
        self.assertEqual(
            classify_revit_name("2.0 PROPOSED SELLING FLOOR PLAN- GROUND"),
            "proposed",
        )
        self.assertEqual(
            classify_revit_name("5.0 OVERLAY- EXISTING & PROPOSED PLAN"),
            "overlay",
        )
        self.assertEqual(
            classify_revit_name("1-0 EXISTING CONDITIONS - GROUND"),
            "existing",
        )
        self.assertEqual(
            classify_revit_name("1131_Marrickville_Selling floor.dwg"),
            "proposed",
        )
        self.assertEqual(
            classify_revit_name("1131_Marrickville_BLD_Existing Conditions.dwg"),
            "existing",
        )
        self.assertTrue(is_proposed_scope("2.0 PROPOSED SELLING FLOOR PLAN- GROUND"))
        self.assertFalse(is_proposed_scope("00-GROUND"))
        self.assertTrue(is_existing_ground_view("1.0 EXISTING CONDITIONS - GROUND"))
        self.assertTrue(is_existing_ground_view("1-0 EXISTING CONDITIONS - GROUND"))
        self.assertFalse(is_existing_ground_view("1.1 EXISTING CONDITIONS - MEZZANINE"))
        self.assertFalse(is_existing_conditions_view("2.0 PROPOSED SELLING FLOOR PLAN- GROUND"))
        self.assertFalse(is_existing_conditions_view("5.0 OVERLAY- EXISTING & PROPOSED PLAN"))
        self.assertFalse(is_existing_conditions_view("EXISTING GONDOLA TRACE - GROUND"))

    def test_never_chooses_proposed_level(self):
        levels = [
            "2.0 PROPOSED SELLING FLOOR PLAN- GROUND",
            "00-GROUND",
            "1-0 EXISTING CONDITIONS - GROUND",
        ]
        self.assertEqual(
            choose_existing_level_name(levels, "00-GROUND"),
            "00-GROUND",
        )
        self.assertEqual(
            choose_existing_level_name(levels, "2.0 PROPOSED SELLING FLOOR PLAN- GROUND"),
            "1-0 EXISTING CONDITIONS - GROUND",
        )
        self.assertIsNone(
            choose_existing_level_name(
                ["2.0 PROPOSED SELLING FLOOR PLAN- GROUND"],
                "2.0 PROPOSED SELLING FLOOR PLAN- GROUND",
            )
        )

    def test_never_chooses_overlay_view(self):
        views = [
            ("5.0 OVERLAY- EXISTING & PROPOSED PLAN", "00-GROUND"),
            ("2.0 PROPOSED SELLING FLOOR PLAN- GROUND", "00-GROUND"),
            ("1-0 EXISTING CONDITIONS - GROUND", "00-GROUND"),
        ]
        self.assertEqual(
            choose_existing_view_name(views, "00-GROUND"),
            "1-0 EXISTING CONDITIONS - GROUND",
        )

    def test_existing_conditions_view_wins_even_on_other_level(self):
        # Marrickville: 1.0 EXISTING CONDITIONS - GROUND is not hosted
        # on 00-GROUND, so placing on 00-GROUND made 1228 families
        # invisible in the view the user had open.
        views = [
            ("5.0 OVERLAY- EXISTING & PROPOSED PLAN", "00-GROUND"),
            ("2.0 PROPOSED SELLING FLOOR PLAN- GROUND", "2.0 PROPOSED SELLING FLOOR PLAN- GROUND"),
            ("1.0 EXISTING CONDITIONS - GROUND", "2.0 PROPOSED SELLING FLOOR PLAN- GROUND"),
        ]
        levels = [
            "00-GROUND",
            "2.0 PROPOSED SELLING FLOOR PLAN- GROUND",
            "1.0 EXISTING CONDITIONS - GROUND",
        ]
        view_name, level_name = choose_existing_placement(
            views, levels, "00-GROUND"
        )
        self.assertEqual(view_name, "1.0 EXISTING CONDITIONS - GROUND")
        self.assertEqual(level_name, "2.0 PROPOSED SELLING FLOOR PLAN- GROUND")
        self.assertEqual(
            choose_existing_view_name(views, "00-GROUND"),
            "1.0 EXISTING CONDITIONS - GROUND",
        )

    def test_preferred_existing_view_name(self):
        views = [
            ("1.1 EXISTING CONDITIONS - MEZZANINE", "00-MEZZ"),
            ("1.0 EXISTING CONDITIONS - GROUND", "1.0 EXISTING CONDITIONS - GROUND"),
        ]
        view_name, level_name = choose_existing_placement(
            views,
            ["00-GROUND", "1.0 EXISTING CONDITIONS - GROUND"],
            "00-GROUND",
            "1.0 EXISTING CONDITIONS - GROUND",
        )
        self.assertEqual(view_name, "1.0 EXISTING CONDITIONS - GROUND")
        self.assertEqual(level_name, "1.0 EXISTING CONDITIONS - GROUND")

    def test_keeps_proposed_layer_when_it_is_the_only_source(self):
        # Existing Conditions exports often put the real store text on a
        # layer called PROPOSED. Dropping that set wrote JSON with 0 items.
        raw = [
            {"text": "15FMCA", "x": 0, "y": 0, "rotation": 0, "layer": "PROPOSED"},
        ]
        gondolas, diag = build_gondolas(raw)
        self.assertEqual(len(gondolas), 1)
        self.assertEqual(gondolas[0]["code"], "15FMCA")
        self.assertEqual(diag["dropped_proposed_layer"], 0)

    def test_drops_proposed_layer_when_existing_labels_remain(self):
        raw = [
            {"text": "15FMCA", "x": 0, "y": 0, "rotation": 0, "layer": "EXISTING"},
            {"text": "21FMCS", "x": 5000, "y": 0, "rotation": 0, "layer": "PROPOSED"},
        ]
        gondolas, diag = build_gondolas(raw)
        codes = [item["code"] for item in gondolas]
        self.assertEqual(codes, ["15FMCA"])
        self.assertEqual(diag["dropped_proposed_layer"], 1)

    def test_keeps_selling_floor_block_when_it_is_the_only_source(self):
        raw = [
            {
                "text": "15FMCA",
                "x": 0,
                "y": 0,
                "rotation": 0,
                "layer": "0",
                "block": "1131_Marrickville_Selling floor",
            },
        ]
        kept, info = keep_existing_source_labels(raw)
        self.assertEqual(len(kept), 1)
        self.assertEqual(info["dropped_proposed_source"], 0)

    def test_drops_selling_floor_block_when_existing_block_exists(self):
        raw = [
            {
                "text": "15F",
                "x": 0,
                "y": 200,
                "rotation": 0,
                "layer": "0",
                "block": "1131_Marrickville_BLD_Existing Conditions",
            },
            {
                "text": "MCA",
                "x": 0,
                "y": 0,
                "rotation": 0,
                "layer": "0",
                "block": "1131_Marrickville_BLD_Existing Conditions",
            },
            {
                "text": "15FMCA",
                "x": 10,
                "y": 100,
                "rotation": 0,
                "layer": "0",
                "block": "1131_Marrickville_Selling floor",
            },
        ]
        kept, info = keep_existing_source_labels(raw)
        self.assertEqual(len(kept), 2)
        self.assertGreaterEqual(info["dropped_proposed_source"], 1)
        self.assertTrue(all("Selling" not in item.get("block", "") for item in kept))

    def test_scans_leftover_when_modelspace_has_only_title_text(self):
        title_only = [{"text": "1-0 EXISTING CONDITIONS - GROUND", "x": 0, "y": 0}]
        self.assertFalse(has_classified_gondola(title_only))
        self.assertTrue(should_scan_leftover(title_only))
        self.assertFalse(should_scan_leftover([
            {"text": "15FMCA", "x": 100, "y": 200}
        ]))
        self.assertFalse(is_layout_block("*U123"))
        self.assertTrue(is_layout_block("*Model_Space"))

    def test_loads_dict_or_list_json(self):
        self.assertEqual(load_gondola_items({"gondolas": [{"code": "A"}]}), [{"code": "A"}])
        self.assertEqual(load_gondola_items([{"code": "B"}]), [{"code": "B"}])
        self.assertEqual(load_gondola_items({"total": 0}), [])

    def test_keeps_same_island_leftover_and_drops_local_coords(self):
        world = [{"text": "15FMCA", "x": 275000, "y": 20000}]
        leftover_world = [{"text": "15F", "x": 276200, "y": 20100}]
        leftover_local = [{"text": "MCA", "x": 400, "y": 200}]
        kept = compatible_leftover_labels(world, leftover_world + leftover_local)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["text"], "15F")

    def test_original_leftover_always_wins_even_when_world_has_more_codes(self):
        # First Marrickville File1: leftover SIZE+TYPE in local mm always
        # won. Do not let a thicker XREF FULL-code set steal the island.
        model = [
            {"text": "15FMCA", "x": 275000 + i * 1200, "y": 20000}
            for i in range(5)
        ]
        leftover = []
        for i, (size, typ) in enumerate((
            ("15F", "MCA"), ("21F", "MCS"), ("15F", "LCS"), ("34F", "MCA"),
        )):
            leftover.append({"text": size, "x": 400 + i * 1200, "y": 200})
            leftover.append({"text": typ, "x": 400 + i * 1200, "y": 0})
        picked, source = pick_label_set(model, leftover)
        self.assertEqual(source, "leftover-always")
        self.assertEqual(len(picked), 8)
        self.assertTrue(all(float(lab["x"]) < 100000 for lab in picked))
        self.assertEqual(estimated_gondola_yield(picked), 4)

    def test_does_not_mix_local_leftover_into_world_modelspace(self):
        model = [{"text": "15FMCA", "x": 275000, "y": 20000}]
        leftover = [
            {"text": "15F", "x": 400, "y": 200},
            {"text": "MCA", "x": 400, "y": 0},
        ]
        picked, source = pick_label_set(model, leftover)
        self.assertEqual(source, "leftover-always")
        self.assertTrue(all(float(lab["x"]) < 100000 for lab in picked))
        xs = [float(lab["x"]) for lab in picked]
        self.assertLess(max(xs) - min(xs), 50000)

    def test_uses_modelspace_only_when_leftover_has_no_codes(self):
        model = [{"text": "15FMCA", "x": 275000, "y": 20000}]
        leftover = [{"text": "1-0 EXISTING CONDITIONS - GROUND", "x": 400, "y": 200}]
        picked, source = pick_label_set(model, leftover)
        self.assertEqual(source, "modelspace")
        self.assertEqual(picked[0]["text"], "15FMCA")

    def test_uses_leftover_when_modelspace_has_no_codes(self):
        leftover = [{"text": "15FMCA", "x": 400, "y": 200}]
        picked, source = pick_label_set(
            [{"text": "1-0 EXISTING CONDITIONS - GROUND", "x": 0, "y": 0}],
            leftover,
        )
        self.assertEqual(source, "leftover-always")
        self.assertEqual(picked[0]["text"], "15FMCA")

    def test_skips_cad_offset_when_json_already_in_world_space(self):
        # Marrickville leftover labels are already near the CAD link origin.
        xs = [275697, 349405, 383050]
        self.assertFalse(should_apply_cad_translation(xs, 274964))
        self.assertTrue(should_apply_cad_translation([733, 38000, 74000], 274964))


class OverlayDedupTests(unittest.TestCase):
    def test_drops_proposed_copy_of_same_bay(self):
        raw = [
            {"text": "15F", "x": 1000, "y": 5200, "rotation": 0, "layer": "EXISTING"},
            {"text": "MCA", "x": 1000, "y": 5000, "rotation": 0, "layer": "EXISTING"},
            {"text": "15FMCA", "x": 1010, "y": 5100, "rotation": 0, "layer": "PROPOSED"},
        ]
        gondolas, diag = build_gondolas(raw)
        self.assertEqual(len(gondolas), 1)
        self.assertGreaterEqual(diag["dropped_overlaps"] + diag["dropped_proposed_layer"], 1)
        self.assertEqual(gondolas[0]["code"], "15FMCA")

    def test_keeps_end_panel_beside_gondola(self):
        raw = [
            {"text": "15FMCA", "x": 0, "y": 0, "rotation": 0},
            {"text": "15SHMC", "x": 200, "y": 0, "rotation": 0},
        ]
        gondolas, _ = build_gondolas(raw)
        codes = sorted(item["code"] for item in gondolas)
        self.assertEqual(codes, ["15FMCA", "15SHMC"])


class AngleTests(unittest.TestCase):
    def test_135_is_diagonal_not_vertical(self):
        self.assertEqual(get_orientation(135), "DIAGONAL")
        self.assertEqual(get_orientation(45), "DIAGONAL")
        self.assertEqual(get_orientation(90), "VERTICAL")
        self.assertEqual(get_orientation(0), "HORIZONTAL")
        self.assertEqual(get_orientation(178), "HORIZONTAL")

    def test_revit_convention(self):
        self.assertEqual(tracing_to_revit_angle(0), 90.0)
        self.assertEqual(tracing_to_revit_angle(90), 0.0)
        self.assertEqual(tracing_to_revit_angle(45), 135.0)
        self.assertEqual(tracing_to_revit_angle(135), 45.0)

    def test_snap(self):
        self.assertEqual(snap_line_angle(8), 0.0)
        self.assertEqual(snap_line_angle(88), 90.0)
        self.assertEqual(snap_line_angle(47), 45.0)

    def test_line_fold(self):
        self.assertEqual(normalize_line_angle(180), 0.0)
        self.assertEqual(normalize_line_angle(270), 90.0)


def rect_segments(cx, cy, length, depth, axis_deg=0.0):
    """Four sides of a rectangle, length along axis_deg."""
    rad = math.radians(axis_deg)
    ux, uy = math.cos(rad), math.sin(rad)
    nx, ny = -uy, ux
    hl, hd = length / 2.0, depth / 2.0
    corners = []
    for sl, sd in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        corners.append((
            cx + ux * hl * sl + nx * hd * sd,
            cy + uy * hl * sl + ny * hd * sd,
        ))
    segs = []
    for i in range(4):
        x1, y1 = corners[i]
        x2, y2 = corners[(i + 1) % 4]
        segs.append((x1, y1, x2, y2))
    return segs


class BayRectangleTests(unittest.TestCase):
    def test_reads_centre_and_axis_of_a_horizontal_bay(self):
        # 1200 along X, 1000 across. Label sits off-centre inside it.
        segs = rect_segments(10600, 5500, 1200, 1000, 0.0)
        rect = bay_rect_from_segments((10450, 5680), segs)
        self.assertIsNotNone(rect)
        self.assertAlmostEqual(rect["x"], 10600, delta=1.0)
        self.assertAlmostEqual(rect["y"], 5500, delta=1.0)
        self.assertAlmostEqual(rect["length"], 1200, delta=1.0)
        self.assertAlmostEqual(rect["depth"], 1000, delta=1.0)
        self.assertAlmostEqual(rect["axis"], 0.0, delta=0.5)

    def test_reads_axis_of_a_vertical_bay(self):
        segs = rect_segments(2000, 9000, 1200, 1000, 90.0)
        rect = bay_rect_from_segments((2100, 9150), segs)
        self.assertIsNotNone(rect)
        self.assertAlmostEqual(rect["x"], 2000, delta=1.0)
        self.assertAlmostEqual(rect["y"], 9000, delta=1.0)
        self.assertAlmostEqual(rect["axis"], 90.0, delta=0.5)

    def test_reads_axis_of_a_forty_five_degree_bay(self):
        segs = rect_segments(3000, 3000, 1200, 900, 135.0)
        rect = bay_rect_from_segments((3050, 3040), segs)
        self.assertIsNotNone(rect)
        self.assertAlmostEqual(rect["axis"], 135.0, delta=1.0)
        self.assertAlmostEqual(rect["length"], 1200, delta=2.0)

    def test_picks_the_bay_holding_the_label_not_the_run_across_the_aisle(self):
        # This is the V5 failure: a bay across the aisle voted for the
        # perpendicular direction, so half the families were 90 out.
        segs = rect_segments(10600, 5500, 1200, 1000, 0.0)
        segs += rect_segments(10600, 9000, 1000, 1200, 90.0)
        rect = bay_rect_from_segments((10600, 5520), segs)
        self.assertIsNotNone(rect)
        self.assertAlmostEqual(rect["y"], 5500, delta=1.0)
        self.assertAlmostEqual(rect["axis"], 0.0, delta=0.5)

    def test_ignores_long_walls_and_tiny_ticks(self):
        segs = rect_segments(10600, 5500, 1200, 1000, 0.0)
        segs.append((0, 5000, 90000, 5000))
        segs.append((10600, 5500, 10620, 5500))
        rect = bay_rect_from_segments((10600, 5500), segs)
        self.assertIsNotNone(rect)
        self.assertAlmostEqual(rect["length"], 1200, delta=1.0)

    def test_returns_none_without_a_closing_rectangle(self):
        self.assertIsNone(bay_rect_from_segments((0, 0), []))
        self.assertIsNone(
            bay_rect_from_segments((0, 0), [(0, 0, 1200, 0)])
        )


class FootprintAlignmentTests(unittest.TestCase):
    def test_bay_axis_prefers_long_axis_field(self):
        self.assertEqual(bay_axis_from_item({"orientation_angle": 0.0}), 0.0)
        self.assertEqual(bay_axis_from_item({"orientation_angle": 90.0}), 90.0)
        self.assertEqual(bay_axis_from_item({"orientation_angle": 180.0}), 0.0)

    def test_bay_axis_converts_family_rotation(self):
        # Old JSON without orientation_angle: revit_angle 90 means a
        # horizontal run, so the bay axis is 0.
        self.assertEqual(bay_axis_from_item({"revit_angle": 90.0}), 0.0)
        self.assertEqual(bay_axis_from_item({"angle": 0.0}), 90.0)
        self.assertEqual(bay_axis_from_item({"orientation": "VERTICAL"}), 90.0)
        self.assertEqual(bay_axis_from_item({}), 0.0)

    def test_wide_footprint_on_horizontal_bay_needs_no_turn(self):
        self.assertEqual(footprint_alignment_delta(4.0, 2.0, 0.0), 0.0)

    def test_wide_footprint_on_vertical_bay_turns_ninety(self):
        self.assertEqual(footprint_alignment_delta(4.0, 2.0, 90.0), 90.0)

    def test_tall_footprint_on_horizontal_bay_turns_back(self):
        # A family already drawn along +Y must turn -90, not +90, so it
        # does not swing onto the neighbouring aisle.
        self.assertEqual(footprint_alignment_delta(2.0, 4.0, 0.0), -90.0)

    def test_diagonal_bay_turns_from_measured_axis(self):
        self.assertEqual(footprint_alignment_delta(4.0, 2.0, 45.0), 45.0)
        self.assertEqual(footprint_alignment_delta(4.0, 2.0, 135.0), -45.0)
        self.assertEqual(footprint_alignment_delta(2.0, 4.0, 135.0), 45.0)

    def test_square_footprint_is_left_alone(self):
        self.assertEqual(footprint_alignment_delta(3.0, 3.0, 90.0), 0.0)

    def test_fold(self):
        self.assertEqual(fold_line_angle(270.0), 90.0)
        self.assertEqual(fold_line_angle(-90.0), 90.0)
        self.assertEqual(fold_line_angle(360.0), 0.0)


class BayDimensionAlignmentTests(unittest.TestCase):
    def test_plan_extent_of_turned_rectangle(self):
        self.assertEqual(plan_extent(1200.0, 900.0, 0.0), (1200.0, 900.0))
        x, y = plan_extent(1200.0, 900.0, 90.0)
        self.assertAlmostEqual(x, 900.0)
        self.assertAlmostEqual(y, 1200.0)
        x, y = plan_extent(1200.0, 900.0, 45.0)
        self.assertAlmostEqual(x, 2100.0 / math.sqrt(2.0))
        self.assertAlmostEqual(y, 2100.0 / math.sqrt(2.0))

    def test_bay_dims_put_the_long_side_first(self):
        self.assertEqual(
            bay_dims_from_item({"bay_length": 900.0, "bay_depth": 1200.0}),
            (1200.0, 900.0),
        )
        self.assertIsNone(bay_dims_from_item({"bay_length": 1200.0}))
        self.assertIsNone(bay_dims_from_item({}))

    def test_without_bay_dims_it_matches_the_long_axis_turn(self):
        self.assertEqual(bay_alignment_delta(4.0, 2.0, 90.0), 90.0)
        self.assertEqual(bay_alignment_delta(2.0, 4.0, 0.0), -90.0)

    def test_bay_dims_keep_the_turn_that_matches_the_drawn_bay(self):
        # Family box 1200 x 1000 traced from a 1200 x 1000 bay running
        # along +Y: it has to end up 1000 across and 1200 deep.
        self.assertEqual(
            bay_alignment_delta(1200.0, 1000.0, 90.0, 1200.0, 1000.0), 90.0
        )
        self.assertEqual(
            bay_alignment_delta(1200.0, 1000.0, 0.0, 1200.0, 1000.0), 0.0
        )

    def test_a_box_wider_than_its_bay_still_turns_the_right_way(self):
        # Revit boxes include header rails and kicks, so the measured box
        # is often longer than the drawn bay. The 90 degree error swaps
        # the extents, which loses by far more than the size difference.
        self.assertEqual(
            bay_alignment_delta(1500.0, 1000.0, 90.0, 1200.0, 1000.0), 90.0
        )
        self.assertEqual(
            bay_alignment_delta(1000.0, 1500.0, 90.0, 1200.0, 1000.0), 0.0
        )

    def test_square_box_is_left_alone_even_with_bay_dims(self):
        self.assertEqual(
            bay_alignment_delta(1000.0, 1000.0, 90.0, 1200.0, 1000.0), 0.0
        )

    def test_fit_error_reports_each_axis(self):
        error = footprint_fit_error(1300.0, 1000.0, 1200.0, 1000.0, 0.0)
        self.assertAlmostEqual(error[0], 100.0)
        self.assertAlmostEqual(error[1], 0.0)
        error = footprint_fit_error(1000.0, 1200.0, 1200.0, 1000.0, 90.0)
        self.assertAlmostEqual(error[0], 0.0)
        self.assertAlmostEqual(error[1], 0.0)
        self.assertIsNone(footprint_fit_error(1.0, 1.0, None, None, 0.0))


class MatchingTests(unittest.TestCase):
    def test_mutual_nearest_avoids_adjacent_bay(self):
        labels = expand_raw_labels([
            {"text": "15F", "x": 0, "y": 200, "rotation": 0},
            {"text": "MCA", "x": 0, "y": 0, "rotation": 0},
            {"text": "15F", "x": 1200, "y": 200, "rotation": 0},
            {"text": "MCS", "x": 1200, "y": 0, "rotation": 0},
        ])
        pairs, _, _, _, _ = match_size_type(labels)
        self.assertEqual(len(pairs), 2)
        codes = sorted(size["text"] + typ["text"] for size, typ, _ in pairs)
        self.assertEqual(codes, ["15FMCA", "15FMCS"])

    def test_does_not_pair_across_1200mm_bay(self):
        labels = expand_raw_labels([
            {"text": "15F", "x": 0, "y": 0, "rotation": 0},
            {"text": "MCA", "x": 1200, "y": 0, "rotation": 0},
        ])
        pairs, _, _, _, _ = match_size_type(labels)
        self.assertEqual(pairs, [])


class OrientationTests(unittest.TestCase):
    def test_south_wall_run_is_horizontal(self):
        # Marrickville south wall: 36WLOA centres 1200 mm apart, y ~ 680.
        raw = []
        for x in (29226, 28026, 26826, 25626, 24426):
            raw.append({"text": "36WLOA", "x": x, "y": 686, "rotation": 0})
        gondolas, _ = build_gondolas(raw)
        self.assertEqual(len(gondolas), 5)
        for gondola in gondolas:
            self.assertEqual(gondola["orientation"], "HORIZONTAL")
            self.assertAlmostEqual(gondola["orientation_angle"], 0.0, places=0)
            self.assertAlmostEqual(gondola["revit_angle"], 90.0, places=0)
            self.assertEqual(gondola["orientation_source"], "NEIGHBOR_RUN")

    def test_west_wall_run_is_vertical(self):
        raw = []
        for y in (8520, 9720, 10970, 12170, 14570):
            raw.append({"text": "36WLOA", "x": 649, "y": y, "rotation": 0})
        gondolas, _ = build_gondolas(raw)
        for gondola in gondolas:
            self.assertEqual(gondola["orientation"], "VERTICAL")
            self.assertAlmostEqual(gondola["orientation_angle"], 90.0, places=0)
            self.assertAlmostEqual(gondola["revit_angle"], 0.0, places=0)

    def test_forty_five_degree_wall(self):
        # Actual Marrickville north-west diagonal: ~1200 mm at 135°.
        points = (
            (3561, 1003),
            (2712, 1852),
            (1864, 2700),
            (1015, 3549),
        )
        raw = [
            {"text": "36WLOA", "x": x, "y": y, "rotation": 0}
            for x, y in points
        ]
        gondolas, _ = build_gondolas(raw)
        for gondola in gondolas:
            self.assertEqual(gondola["orientation"], "DIAGONAL")
            self.assertAlmostEqual(gondola["orientation_angle"], 135.0, places=0)
            self.assertAlmostEqual(gondola["revit_angle"], 45.0, places=0)

    def test_pair_stack_does_not_override_run(self):
        # Upright two-line labels on a horizontal run used to vote VERTICAL
        # because SIZE sat above TYPE.
        raw = []
        for x in (12000, 13200, 14400, 15600):
            raw.append({"text": "15F", "x": x, "y": 5400, "rotation": 0})
            raw.append({"text": "LCS", "x": x, "y": 5100, "rotation": 0})
        gondolas, diag = build_gondolas(raw)
        self.assertEqual(len(gondolas), 4)
        self.assertEqual(diag["pairs"], 4)
        for gondola in gondolas:
            self.assertEqual(gondola["orientation"], "HORIZONTAL")
            self.assertAlmostEqual(gondola["revit_angle"], 90.0, places=0)


class DynamoAngleReaderTests(unittest.TestCase):
    def test_ignores_zero_text_rotation(self):
        item = {
            "rotation": 0.0,
            "orientation_angle": 0.0,
            "revit_angle": 90.0,
            "angle": 90.0,
        }
        self.assertEqual(pick_json_angle(item), 90.0)

    def test_old_json_without_revit_angle_converts_axis(self):
        item = {
            "rotation": 0.0,
            "orientation_angle": 90.0,
        }
        self.assertEqual(pick_json_angle(item), 0.0)

    def test_does_not_use_rotation_key(self):
        item = {"rotation": 0.0}
        self.assertIsNone(pick_json_angle(item))


class ApplyOrientationCleanupTests(unittest.TestCase):
    def test_strips_internal_fields(self):
        gondolas = apply_orientations([{
            "code": "15FMCA",
            "x": 0,
            "y": 0,
            "orientation_source": "DEFAULT_HORIZONTAL",
            "_fallback_axis": 0.0,
            "text_rotation_snapped": 0.0,
        }])
        self.assertNotIn("_fallback_axis", gondolas[0])
        self.assertNotIn("text_rotation_snapped", gondolas[0])

    def test_json_fields_drive_dynamo_rotation(self):
        raw = [
            {"text": "36WLOA", "x": x, "y": 686, "rotation": 0}
            for x in (12000, 13200, 14400)
        ]
        gondolas, _ = build_gondolas(raw)
        item = gondolas[0]
        for key in ("code", "x", "y", "orientation", "orientation_angle",
                    "revit_angle", "angle", "orientation_source"):
            self.assertIn(key, item)
        self.assertEqual(item["rotation"], 0)
        self.assertEqual(pick_json_angle(item), 90.0)
        self.assertNotEqual(pick_json_angle(item), item["rotation"])


if __name__ == "__main__":
    unittest.main()
