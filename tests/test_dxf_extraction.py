import os
import tempfile
import unittest

import ezdxf

from Gondola_OrientationDetector import extract_with_orientation


def _add_rect(msp, x, y, w, h, layer="GONDOLA"):
    pts = [
        (x, y),
        (x + w, y),
        (x + w, y + h),
        (x, y + h),
    ]
    msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": layer})


class DxfExtractionTests(unittest.TestCase):
    def test_end_to_end_horizontal_and_vertical_bays(self):
        doc = ezdxf.new("R2010")
        doc.header["$INSUNITS"] = 4  # millimetres
        msp = doc.modelspace()

        # East-west bay: 1800 x 700, labels stacked in Y.
        _add_rect(msp, 0, 0, 1800, 700)
        msp.add_text(
            "15F",
            dxfattribs={"height": 80, "layer": "TEXT", "insert": (900, 420)},
        )
        msp.add_text(
            "MCA",
            dxfattribs={"height": 80, "layer": "TEXT", "insert": (900, 280)},
        )

        # North-south bay: 700 x 1800, labels stacked in X.
        _add_rect(msp, 4000, 0, 700, 1800)
        msp.add_text(
            "21F",
            dxfattribs={"height": 80, "layer": "TEXT", "insert": (4280, 900)},
        )
        msp.add_text(
            "LCS",
            dxfattribs={"height": 80, "layer": "TEXT", "insert": (4420, 900)},
        )

        # Neighbour bay that previously stole TYPE via greedy matching.
        _add_rect(msp, 2200, 0, 1800, 700)
        msp.add_text(
            "15F",
            dxfattribs={"height": 80, "layer": "TEXT", "insert": (3100, 420)},
        )
        msp.add_text(
            "MCS",
            dxfattribs={"height": 80, "layer": "TEXT", "insert": (3100, 280)},
        )

        # Complete code with geometry.
        _add_rect(msp, 0, 3000, 1500, 600)
        msp.add_text(
            "15ELC",
            dxfattribs={"height": 80, "layer": "TEXT", "insert": (750, 3300)},
        )

        handle, path = tempfile.mkstemp(suffix=".dxf")
        os.close(handle)
        try:
            doc.saveas(path)
            gondolas, extras = extract_with_orientation(path)
        finally:
            os.remove(path)

        codes = sorted(g["code"] for g in gondolas)
        self.assertIn("15FMCA", codes)
        self.assertIn("15FMCS", codes)
        self.assertIn("21FLCS", codes)
        self.assertIn("15ELC", codes)

        by_code = {}
        for g in gondolas:
            by_code.setdefault(g["code"], []).append(g)

        horiz = by_code["15FMCA"][0]
        self.assertEqual(horiz["orientation"], "HORIZONTAL")
        self.assertLess(abs(horiz["orientation_angle"] % 180), 8)

        vert = by_code["21FLCS"][0]
        self.assertEqual(vert["orientation"], "VERTICAL")
        self.assertLess(abs(vert["orientation_angle"] - 90), 8)

        self.assertEqual(extras["unmatched_size"], [])
        self.assertEqual(extras["unmatched_type"], [])


if __name__ == "__main__":
    unittest.main()
