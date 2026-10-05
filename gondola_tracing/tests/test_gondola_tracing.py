import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from gondola_lib import (
    apply_orientations,
    build_gondolas,
    canonical_code,
    expand_raw_labels,
    get_orientation,
    identify_text,
    is_noise_label,
    match_size_type,
    merge_nearby_phrases,
    normalize_line_angle,
    pick_json_angle,
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
