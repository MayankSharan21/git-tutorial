import math
import unittest

from gondola_tracing_lib import (
    apply_cad_transform,
    classify_orientation,
    estimate_gondola_axis,
    match_size_type_pairs,
    normalize_code,
    preferred_json_angle,
    snap_axis_angle,
    text_visual_point,
    unsigned_angle_from_offset,
)


class NormalizeCodeTests(unittest.TestCase):
    def test_mtext_formatting(self):
        self.assertEqual(
            normalize_code(r"{\fArial|b0|i0|c0|p34;15F}"),
            "15F",
        )

    def test_whitespace_and_case(self):
        self.assertEqual(normalize_code("  straight   rail "), "STRAIGHT RAIL")


class AxisHeuristicTests(unittest.TestCase):
    def test_stacked_labels_on_horizontal_bay(self):
        """SIZE above TYPE on an east-west gondola must not become 90°."""
        result = estimate_gondola_axis(
            px=0.0,
            py=0.0,
            pair_dx=0.0,
            pair_dy=350.0,
            pair_dist=350.0,
            label_rotation=0.0,
            segments=[],
        )
        self.assertEqual(result["orientation"], "HORIZONTAL")
        self.assertAlmostEqual(result["orientation_angle"], 0.0, places=3)

    def test_stacked_labels_on_vertical_bay(self):
        result = estimate_gondola_axis(
            px=0.0,
            py=0.0,
            pair_dx=400.0,
            pair_dy=0.0,
            pair_dist=400.0,
            label_rotation=90.0,
            segments=[],
        )
        self.assertEqual(result["orientation"], "VERTICAL")
        self.assertAlmostEqual(result["orientation_angle"], 90.0, places=3)

    def test_geometry_overrides_noisy_pair(self):
        segments = [
            (0.0, -300.0, 1800.0, -300.0),
            (0.0, 300.0, 1800.0, 300.0),
            (0.0, -300.0, 0.0, 300.0),
            (1800.0, -300.0, 1800.0, 300.0),
        ]
        result = estimate_gondola_axis(
            px=900.0,
            py=0.0,
            pair_dx=40.0,
            pair_dy=320.0,
            pair_dist=math.hypot(40.0, 320.0),
            label_rotation=12.0,
            segments=segments,
        )
        self.assertEqual(result["axis_source"], "cad_geometry")
        self.assertEqual(result["orientation"], "HORIZONTAL")

    def test_cardinal_snap(self):
        snapped, src = snap_axis_angle(2.5)
        self.assertEqual(snapped, 0.0)
        self.assertEqual(src, "snap_0")
        snapped, src = snap_axis_angle(44.0)
        self.assertEqual(snapped, 45.0)


class PairingTests(unittest.TestCase):
    def test_mutual_nearest_does_not_steal(self):
        sizes = [
            {"text": "15F", "x": 0.0, "y": 0.0, "label_rotation": 0.0, "layer": "A"},
            {"text": "15F", "x": 1200.0, "y": 0.0, "label_rotation": 0.0, "layer": "A"},
        ]
        types = [
            {"text": "MCA", "x": 0.0, "y": 300.0, "label_rotation": 0.0, "layer": "A"},
            {"text": "MCS", "x": 1200.0, "y": 300.0, "label_rotation": 0.0, "layer": "A"},
        ]
        matches = match_size_type_pairs(sizes, types)
        matched = {
            (sizes[si]["x"], types[ti]["text"]) for si, ti, _dist in matches
        }
        self.assertEqual(matched, {(0.0, "MCA"), (1200.0, "MCS")})

    def test_far_labels_are_not_paired(self):
        sizes = [{"text": "15F", "x": 0.0, "y": 0.0, "label_rotation": 0.0, "layer": "A"}]
        types = [{"text": "MCA", "x": 5000.0, "y": 0.0, "label_rotation": 0.0, "layer": "A"}]
        self.assertEqual(match_size_type_pairs(sizes, types), [])


class JsonAnglePriorityTests(unittest.TestCase):
    def test_ignores_text_rotation(self):
        gondola = {
            "rotation": 90.0,
            "orientation_angle": 0.0,
            "placement_angle": 180.0,
        }
        self.assertEqual(preferred_json_angle(gondola), 180.0)

    def test_falls_back_to_orientation_angle(self):
        gondola = {"rotation": 12.0, "orientation_angle": 90.0}
        self.assertEqual(preferred_json_angle(gondola), 90.0)


class TransformTests(unittest.TestCase):
    def test_identity_transform(self):
        x, y = apply_cad_transform(304.8, 609.6, 0, 0, 1, 0, 0, 1)
        self.assertAlmostEqual(x, 1.0, places=6)
        self.assertAlmostEqual(y, 2.0, places=6)

    def test_translated_and_rotated_90(self):
        # CAD +X maps to Revit +Y (90° CCW), origin at (10, 20) ft.
        x, y = apply_cad_transform(
            304.8,
            0.0,
            origin_x_ft=10.0,
            origin_y_ft=20.0,
            basis_xx=0.0,
            basis_xy=1.0,
            basis_yx=-1.0,
            basis_yy=0.0,
        )
        self.assertAlmostEqual(x, 10.0, places=6)
        self.assertAlmostEqual(y, 21.0, places=6)


class MiscTests(unittest.TestCase):
    def test_unsigned_offset(self):
        self.assertEqual(unsigned_angle_from_offset(10, 0), 0.0)
        self.assertEqual(unsigned_angle_from_offset(0, 10), 90.0)
        self.assertEqual(unsigned_angle_from_offset(-10, 0), 0.0)

    def test_classify(self):
        self.assertEqual(classify_orientation(0), "HORIZONTAL")
        self.assertEqual(classify_orientation(90), "VERTICAL")
        self.assertEqual(classify_orientation(45), "DIAGONAL")

    def test_text_visual_left_baseline_shifts_along_and_up(self):
        x, y = text_visual_point(
            0, 0, 0, 100, "15F", halign=0, valign=0
        )
        self.assertGreater(x, 0)
        self.assertGreater(y, 0)


if __name__ == "__main__":
    unittest.main()
