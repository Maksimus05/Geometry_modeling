"""Графические примитивы сцены."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from geometry import Point, Segment

if TYPE_CHECKING:
    from canvas_view import WorkCanvas


class Shape(ABC):
    """Базовый класс для всех фигур, которые можно хранить и рисовать."""

    @abstractmethod
    def draw(self, canvas: WorkCanvas, *, index: int, active: bool) -> None:
        """Отрисовать фигуру на рабочем холсте."""

    @abstractmethod
    def title(self, index: int) -> str:
        """Короткая строка для списка объектов."""


@dataclass
class SegmentShape(Shape):
    segment: Segment

    @property
    def p1(self) -> Point:
        return self.segment.p1

    @property
    def p2(self) -> Point:
        return self.segment.p2

    @property
    def length(self) -> float:
        return self.segment.length

    @property
    def inclination_rad(self) -> float:
        return self.segment.inclination_rad

    def set_points(self, p1: Point, p2: Point) -> None:
        self.segment = Segment(p1, p2)

    def draw(self, canvas: WorkCanvas, *, index: int, active: bool) -> None:
        canvas.draw_segment(self.segment, index=index, active=active)

    def title(self, index: int) -> str:
        p1 = self.segment.p1
        p2 = self.segment.p2
        return f"{index}: отрезок ({p1.x:g}; {p1.y:g}) - ({p2.x:g}; {p2.y:g})"
