"""Рабочая область: сетка, оси и отрезок."""

from __future__ import annotations

import tk_bootstrap  # noqa: F401  — пути Tcl/Tk до импорта tkinter

import tkinter as tk
from typing import Callable, Optional

from geometry import Point, Segment
from shapes import Shape


class WorkCanvas(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        *,
        on_point: Optional[Callable[[Point], None]] = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("cursor", "crosshair")
        super().__init__(master, **kwargs)

        self.on_point = on_point
        self.grid_step = 1.0
        self.bg_color = "#f7f4ea"
        self.grid_color = "#cfc8b8"
        self.axis_color = "#3d3a32"
        self.segment_color = "#1f4e79"
        self.point_color = "#b03a2e"
        self.objects: list[Shape] = []
        self.selected_index: Optional[int] = None
        self.preview: Optional[Point] = None

        self._scale = 40.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._drag: Optional[tuple[int, int]] = None

        self.configure(bg=self.bg_color)
        self.bind("<Configure>", lambda _e: self.redraw())
        self.bind("<Button-1>", self._on_click)
        self.bind("<Motion>", self._on_motion)
        self.bind("<ButtonPress-2>", self._start_pan)
        self.bind("<B2-Motion>", self._do_pan)
        self.bind("<ButtonPress-3>", self._start_pan)
        self.bind("<B3-Motion>", self._do_pan)
        self.bind("<MouseWheel>", self._on_wheel)

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
        cx = self.winfo_width() / 2 + self._offset_x
        cy = self.winfo_height() / 2 + self._offset_y
        return cx + x * self._scale, cy - y * self._scale

    def screen_to_world(self, sx: float, sy: float) -> Point:
        cx = self.winfo_width() / 2 + self._offset_x
        cy = self.winfo_height() / 2 + self._offset_y
        return Point((sx - cx) / self._scale, (cy - sy) / self._scale)

    def _on_click(self, event: tk.Event) -> None:
        if self.on_point:
            self.on_point(self.screen_to_world(event.x, event.y))

    def _on_motion(self, event: tk.Event) -> None:
        self._cursor = self.screen_to_world(event.x, event.y)
        self.redraw()

    def _start_pan(self, event: tk.Event) -> None:
        self._drag = (event.x, event.y)

    def _do_pan(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        dx = event.x - self._drag[0]
        dy = event.y - self._drag[1]
        self._offset_x += dx
        self._offset_y += dy
        self._drag = (event.x, event.y)
        self.redraw()

    def _on_wheel(self, event: tk.Event) -> None:
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        new_scale = min(max(self._scale * factor, 8.0), 400.0)
        before = self.screen_to_world(event.x, event.y)
        self._scale = new_scale
        after = self.screen_to_world(event.x, event.y)
        self._offset_x += (after.x - before.x) * self._scale
        self._offset_y -= (after.y - before.y) * self._scale
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        self._draw_grid(w, h)
        self._draw_axes(w, h)
        for i, shape in enumerate(self.objects):
            active = i == self.selected_index if self.selected_index is not None else i == len(self.objects) - 1
            shape.draw(self, index=i + 1, active=active)
        if self.preview is not None:
            self._draw_point(self.preview, "P1")
        cursor = getattr(self, "_cursor", None)
        if cursor is not None:
            self._draw_cursor_hint(cursor)

    def _visible_world_bounds(self, w: int, h: int) -> tuple[float, float, float, float]:
        p0 = self.screen_to_world(0, h)
        p1 = self.screen_to_world(w, 0)
        return p0.x, p1.x, p0.y, p1.y

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
        self.create_text(w - 18, y0 - 12, text="X", fill=self.axis_color, font=("Segoe UI", 11, "bold"))
        self.create_text(ox + 14, 16, text="Y", fill=self.axis_color, font=("Segoe UI", 11, "bold"))

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
