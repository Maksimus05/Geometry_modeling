"""Проверки преобразований координат."""

import math
import unittest

from geometry import Point, Segment, to_degrees, to_radians
from shapes import SegmentShape, Shape


class GeometryTests(unittest.TestCase):
    def test_polar_roundtrip(self) -> None:
        p = Point(3, 4)
        r, th = p.polar()
        self.assertAlmostEqual(r, 5)
        back = Point.from_polar(r, th)
        self.assertAlmostEqual(back.x, 3)
        self.assertAlmostEqual(back.y, 4)

    def test_segment_metrics(self) -> None:
        s = Segment(Point(0, 0), Point(1, 1))
        self.assertAlmostEqual(s.length, math.sqrt(2))
        self.assertAlmostEqual(to_degrees(s.inclination_rad), 45)
        self.assertAlmostEqual(to_radians(90), math.pi / 2)

    def test_second_point_from_segment_polar_vector(self) -> None:
        start = Point(2, 3)
        vector = Point.from_polar(5, to_radians(0))
        end = Point(start.x + vector.x, start.y + vector.y)
        self.assertAlmostEqual(end.x, 7)
        self.assertAlmostEqual(end.y, 3)

    def test_segment_shape_is_scene_shape(self) -> None:
        shape = SegmentShape(Segment(Point(0, 0), Point(3, 4)))
        self.assertIsInstance(shape, Shape)
        self.assertAlmostEqual(shape.length, 5)


if __name__ == "__main__":
    unittest.main()
