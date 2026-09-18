"""Рабочая область: сетка, оси и навигация вида."""

from __future__ import annotations

import tk_bootstrap  # noqa: F401  — пути Tcl/Tk до импорта tkinter

import math
import tkinter as tk
from typing import Callable, Optional

from geometry import Point, Segment
from shapes import SegmentShape, Shape


class WorkCanvas(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        *,
        on_point: Optional[Callable[[Point], None]] = None,
        on_view_change: Optional[Callable[[], None]] = None,
        on_cursor_change: Optional[Callable[[Optional[Point]], None]] = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("cursor", "crosshair")
        super().__init__(master, **kwargs)

        self.on_point = on_point
        self.on_view_change = on_view_change
        self.on_cursor_change = on_cursor_change
        self.grid_step = 1.0
        self.bg_color = "#f7f4ea"
        self.grid_color = "#cfc8b8"
        self.axis_color = "#3d3a32"
        self.segment_color = "#1f4e79"
        self.point_color = "#b03a2e"
        self.objects: list[Shape] = []
        self.selected_index: Optional[int] = None
        self.preview: Optional[Point] = None
        self.active_tool = "draw"

        self._scale = 40.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._rotation = 0.0
        self._drag: Optional[tuple[int, int, str]] = None
        self._cursor: Optional[Point] = None

        self.configure(bg=self.bg_color)
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonPress-1>", self._on_button1_press, add="+")
        self.bind("<B1-Motion>", self._do_pan)
        self.bind("<ButtonRelease-1>", self._end_pan)
        self.bind("<Motion>", self._on_motion)
        self.bind("<ButtonPress-2>", self._start_pan)
        self.bind("<B2-Motion>", self._do_pan)
        self.bind("<ButtonRelease-2>", self._end_pan)
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", lambda event: self.zoom_at(event.x, event.y, 1.1))
        self.bind("<Button-5>", lambda event: self.zoom_at(event.x, event.y, 1 / 1.1))

    @property
    def scale_percent(self) -> float:
        return self._scale / 40.0 * 100.0

    @property
    def rotation_degrees(self) -> float:
        return math.degrees(self._rotation)

    @property
    def cursor_world(self) -> Optional[Point]:
        return self._cursor

    @property
    def tool_title(self) -> str:
        return "Рука" if self.active_tool == "pan" else "Построение"

    def set_tool(self, tool: str) -> None:
        # переключение инструмента Рука
        # Инструмент меняет только режим взаимодействия, объекты чертежа не меняются.
        self.active_tool = tool
        self.configure(cursor="fleur" if tool == "pan" else "crosshair")
        self._notify_view()

    def set_objects(self, objects: list[Shape]) -> None:
        self.objects = list(objects)
        if self.selected_index is not None and self.selected_index >= len(self.objects):
            self.selected_index = len(self.objects) - 1 if self.objects else None
        self.preview = None
        self.redraw()

    def set_segments(self, segments: list[Segment]) -> None:
        from shapes import SegmentShape

        self.set_objects([SegmentShape(segment) for segment in segments])

    def set_selected_index(self, index: Optional[int]) -> None:
        self.selected_index = index
        self.redraw()

    def set_preview(self, point: Optional[Point]) -> None:
        self.preview = point
        self.redraw()

    def apply_colors(self, *, bg: str, grid: str, segment: str) -> None:
        self.bg_color = bg
        self.grid_color = grid
        self.segment_color = segment
        self.configure(bg=bg)
        self.redraw()

    def set_grid_step(self, step: float) -> None:
        self.grid_step = max(step, 0.01)
        self.redraw()

    def world_to_screen(self, x: float, y: float) -> tuple[float, float]:
        # перевод мировых координат в экранные
        # Прямое видовое преобразование: мир -> экран с учетом поворота, масштаба и сдвига.
        cx = self.winfo_width() / 2 + self._offset_x
        cy = self.winfo_height() / 2 + self._offset_y
        cos_a = math.cos(self._rotation)
        sin_a = math.sin(self._rotation)
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        return cx + rx * self._scale, cy - ry * self._scale

    def screen_to_world(self, sx: float, sy: float) -> Point:
        # обратный перевод координат мыши в координаты чертежа
        # Обратное преобразование: координаты мыши на экране -> координаты чертежа.
        cx = self.winfo_width() / 2 + self._offset_x
        cy = self.winfo_height() / 2 + self._offset_y
        rx = (sx - cx) / self._scale
        ry = (cy - sy) / self._scale
        cos_a = math.cos(self._rotation)
        sin_a = math.sin(self._rotation)
        return Point(rx * cos_a + ry * sin_a, -rx * sin_a + ry * cos_a)

    def _on_click(self, event: tk.Event) -> None:
        if self.active_tool == "pan":
            return
        # Точка клика сохраняется в мировой системе, а не в пикселях экрана.
        if self.on_point:
            self.on_point(self.screen_to_world(event.x, event.y))

    def _on_motion(self, event: tk.Event) -> None:
        self._cursor = self.screen_to_world(event.x, event.y)
        if self.on_cursor_change:
            self.on_cursor_change(self._cursor)
        self.redraw()

    def _on_button1_press(self, event: tk.Event) -> None:
        if self.active_tool == "pan":
            self._start_pan(event)

    def _start_pan(self, event: tk.Event) -> None:
        self._drag = (event.x, event.y, "middle")

    def _end_pan(self, _event: tk.Event) -> None:
        self._drag = None

    def _do_pan(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        # панорамирование
        # "Рука" двигает камеру: меняются смещения вида, координаты объектов остаются прежними.
        dx = event.x - self._drag[0]
        dy = event.y - self._drag[1]
        self._offset_x += dx
        self._offset_y += dy
        self._drag = (event.x, event.y, self._drag[2])
        self.redraw()
        self._notify_view()

    def _on_wheel(self, event: tk.Event) -> None:
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self.zoom_at(event.x, event.y, factor)

    def zoom_at(self, sx: float, sy: float, factor: float) -> None:
        # масштабирование лупой относительно точки
        # Лупа масштабирует относительно опорной точки: под курсором остается та же мировая точка.
        anchor = self.screen_to_world(sx, sy)
        self._scale = min(max(self._scale * factor, 8.0), 400.0)
        anchor_sx, anchor_sy = self.world_to_screen(anchor.x, anchor.y)
        self._offset_x += sx - anchor_sx
        self._offset_y += sy - anchor_sy
        self.redraw()
        self._notify_view()

    def zoom_center(self, factor: float) -> None:
        # Кнопки "Лупа+" и "Лупа-" используют центр окна как точку масштабирования.
        self.zoom_at(self.winfo_width() / 2, self.winfo_height() / 2, factor)

    def rotate_view(self, degrees: float, *, snap: bool = False) -> None:
        # Поворот выполняется вокруг текущего центра обзора, как поворот камеры над сценой.
        center_sx = self.winfo_width() / 2
        center_sy = self.winfo_height() / 2
        center = self.screen_to_world(center_sx, center_sy)
        self._rotation += math.radians(degrees)
        if snap:
            self._rotation = math.radians(round(math.degrees(self._rotation) / 90.0) * 90.0)
        center_after_sx, center_after_sy = self.world_to_screen(center.x, center.y)
        self._offset_x += center_sx - center_after_sx
        self._offset_y += center_sy - center_after_sy
        self.redraw()
        self._notify_view()

    def reset_view(self) -> None:
        self._scale = 40.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._rotation = 0.0
        self.redraw()
        self._notify_view()

    def fit_all(self) -> None:
        bounds = self._objects_bounds()
        if bounds is None:
            self.reset_view()
            return
        xmin, xmax, ymin, ymax = bounds
        width = max(xmax - xmin, self.grid_step)
        height = max(ymax - ymin, self.grid_step)
        margin = 80
        usable_w = max(self.winfo_width() - margin * 2, 1)
        usable_h = max(self.winfo_height() - margin * 2, 1)
        self._rotation = 0.0
        self._scale = min(max(min(usable_w / width, usable_h / height), 8.0), 400.0)
        self._offset_x = 0.0
        self._offset_y = 0.0
        center = Point((xmin + xmax) / 2, (ymin + ymax) / 2)
        sx, sy = self.world_to_screen(center.x, center.y)
        self._offset_x += self.winfo_width() / 2 - sx
        self._offset_y += self.winfo_height() / 2 - sy
        self.redraw()
        self._notify_view()

    def _objects_bounds(self) -> Optional[tuple[float, float, float, float]]:
        points: list[Point] = []
        for shape in self.objects:
            if isinstance(shape, SegmentShape):
                points.extend([shape.p1, shape.p2])
        if self.preview is not None:
            points.append(self.preview)
        if not points:
            return None
        xs = [p.x for p in points]
        ys = [p.y for p in points]
        return min(xs), max(xs), min(ys), max(ys)

    def _notify_view(self) -> None:
        if self.on_view_change:
            self.on_view_change()

    def redraw(self) -> None:
        # рендер сцены
        # Рендер каждый кадр строится заново из виртуальных объектов и текущей видовой матрицы.
        # Сначала очищаем экран, чтобы старые пиксельные изображения объектов не оставались на холсте.
        self.delete("all")
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        # Сетка и оси тоже находятся в виртуальном пространстве, поэтому реагируют на масштаб и поворот.
        self._draw_grid(w, h)
        self._draw_axes(w, h)
        # Все фигуры хранятся в мировых координатах, а при рисовании переводятся в координаты экрана.
        for i, shape in enumerate(self.objects):
            active = i == self.selected_index if self.selected_index is not None else i == len(self.objects) - 1
            shape.draw(self, index=i + 1, active=active)
        if self.preview is not None:
            # Предпросмотр первой точки рисуется поверх сетки и объектов.
            self._draw_point(self.preview, "P1")
        if self._cursor is not None:
            # Подсказка курсора показывает связь мыши с мировыми координатами.
            self._draw_cursor_hint(self._cursor)

    def _visible_world_bounds(self, w: int, h: int) -> tuple[float, float, float, float]:
        corners = [
            self.screen_to_world(0, 0),
            self.screen_to_world(w, 0),
            self.screen_to_world(0, h),
            self.screen_to_world(w, h),
        ]
        xs = [p.x for p in corners]
        ys = [p.y for p in corners]
        return min(xs), max(xs), min(ys), max(ys)

    def _draw_grid(self, w: int, h: int) -> None:
        xmin, xmax, ymin, ymax = self._visible_world_bounds(w, h)
        step = self.grid_step
        start_x = int(xmin / step) * step
        start_y = int(ymin / step) * step
        x = start_x
        while x <= xmax + 1e-9:
            sx1, sy1 = self.world_to_screen(x, ymin)
            sx2, sy2 = self.world_to_screen(x, ymax)
            self.create_line(sx1, sy1, sx2, sy2, fill=self.grid_color, width=1)
            x += step
        y = start_y
        while y <= ymax + 1e-9:
            sx1, sy1 = self.world_to_screen(xmin, y)
            sx2, sy2 = self.world_to_screen(xmax, y)
            self.create_line(sx1, sy1, sx2, sy2, fill=self.grid_color, width=1)
            y += step

    def _draw_axes(self, w: int, h: int) -> None:
        xmin, xmax, ymin, ymax = self._visible_world_bounds(w, h)
        x1, y0 = self.world_to_screen(xmin, 0)
        x2, y0b = self.world_to_screen(xmax, 0)
        ox, y1 = self.world_to_screen(0, ymin)
        oxb, y2 = self.world_to_screen(0, ymax)
        self.create_line(x1, y0, x2, y0b, fill=self.axis_color, width=2, arrow=tk.LAST)
        self.create_line(ox, y1, oxb, y2, fill=self.axis_color, width=2, arrow=tk.LAST)
        oxs, oys = self.world_to_screen(0, 0)
        self.create_text(oxs + 14, oys + 14, text="O", fill=self.axis_color, font=("Segoe UI", 10, "bold"))
        self.create_text(x2, y0b - 12, text="X", fill=self.axis_color, font=("Segoe UI", 11, "bold"))
        self.create_text(oxb + 14, y2, text="Y", fill=self.axis_color, font=("Segoe UI", 11, "bold"))

        step = self.grid_step
        xmin_t, xmax_t, ymin_t, ymax_t = xmin, xmax, ymin, ymax
        x = int(xmin_t / step) * step
        while x <= xmax_t + 1e-9:
            if abs(x) > 1e-9:
                sx, sy = self.world_to_screen(x, 0)
                self.create_line(sx, sy - 4, sx, sy + 4, fill=self.axis_color)
                label = f"{x:g}"
                self.create_text(sx, sy + 14, text=label, fill=self.axis_color, font=("Segoe UI", 8))
            x += step
        y = int(ymin_t / step) * step
        while y <= ymax_t + 1e-9:
            if abs(y) > 1e-9:
                sx, sy = self.world_to_screen(0, y)
                self.create_line(sx - 4, sy, sx + 4, sy, fill=self.axis_color)
                self.create_text(sx - 16, sy, text=f"{y:g}", fill=self.axis_color, font=("Segoe UI", 8))
            y += step

    def _draw_point(self, p: Point, label: str) -> None:
        sx, sy = self.world_to_screen(p.x, p.y)
        r = 5
        self.create_oval(sx - r, sy - r, sx + r, sy + r, fill=self.point_color, outline="#5d1a14")
        self.create_text(sx + 12, sy - 12, text=label, fill=self.point_color, font=("Segoe UI", 9, "bold"), anchor="w")

    def draw_segment(self, segment: Segment, *, index: int, active: bool) -> None:
        x1, y1 = self.world_to_screen(segment.p1.x, segment.p1.y)
        x2, y2 = self.world_to_screen(segment.p2.x, segment.p2.y)
        width = 4 if active else 3
        self.create_line(x1, y1, x2, y2, fill=self.segment_color, width=width, capstyle=tk.ROUND)
        self._draw_point(segment.p1, f"{index}")
        self._draw_point(segment.p2, f"{index}'")

    def _draw_cursor_hint(self, p: Point) -> None:
        sx, sy = self.world_to_screen(p.x, p.y)
        self.create_text(
            10,
            self.winfo_height() - 12,
            text=f"курсор: x={p.x:.3f}, y={p.y:.3f}",
            anchor="sw",
            fill="#5a564c",
            font=("Segoe UI", 9),
        )
        self.create_line(sx - 6, sy, sx + 6, sy, fill="#7a7466")
        self.create_line(sx, sy - 6, sx, sy + 6, fill="#7a7466")
