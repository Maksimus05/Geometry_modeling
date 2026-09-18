"""САПР ЛР №1: отрезок в декартовых и полярных координатах."""

from __future__ import annotations

import tk_bootstrap  # noqa: F401  — пути Tcl/Tk до импорта tkinter

import tkinter as tk
import math
from tkinter import colorchooser, messagebox, ttk
from typing import Optional

from canvas_view import WorkCanvas
from geometry import Point, Segment, format_angle, to_radians
from shapes import SegmentShape, Shape


class SaprApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("САПР · ЛР №1 — Отрезок как базовый элемент")
        self.geometry("1280x760")
        self.minsize(980, 620)
        self.configure(bg="#e8e4d8")

        self.coord_mode = tk.StringVar(value="cartesian")
        self.angle_mode = tk.StringVar(value="degrees")
        self.grid_step = tk.StringVar(value="1")
        self.bg_color = "#f7f4ea"
        self.grid_color = "#cfc8b8"
        self.segment_color = "#1f4e79"

        self._objects: list[Shape] = []
        self._p1: Optional[Point] = None
        self._p2: Optional[Point] = None
        self._awaiting = 0
        self._selected_index: Optional[int] = None

        self._build_style()
        self._build_ui()
        self._refresh_fields_mode()
        self._refresh_segment_editor()
        self._update_info()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Root.TFrame", background="#e8e4d8")
        style.configure("Panel.TFrame", background="#f3efe4")
        style.configure("Toolbar.TFrame", background="#d9d2c3")
        style.configure("Title.TLabel", background="#f3efe4", font=("Segoe UI", 11, "bold"), foreground="#2c2a24")
        style.configure("Hint.TLabel", background="#f3efe4", font=("Segoe UI", 8), foreground="#6b665c")
        style.configure("Info.TLabel", background="#f3efe4", font=("Consolas", 10), foreground="#2c2a24")
        style.configure("TLabel", background="#f3efe4", font=("Segoe UI", 9))
        style.configure("TRadiobutton", background="#f3efe4", font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("Tool.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 6))

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self, style="Toolbar.TFrame", padding=(10, 8))
        toolbar.pack(fill=tk.X, side=tk.TOP)
        ttk.Button(toolbar, text="Отрезок", style="Tool.TButton", command=self.start_segment).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text="Удалить", style="Tool.TButton", command=self.delete_last).pack(side=tk.LEFT, padx=4)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(toolbar, text="Цвет отрезка", command=lambda: self._pick_color("segment")).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Цвет фона", command=lambda: self._pick_color("bg")).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Цвет сетки", command=lambda: self._pick_color("grid")).pack(side=tk.LEFT, padx=3)
        ttk.Button(toolbar, text="Построить по полям", command=self.build_from_fields).pack(side=tk.RIGHT, padx=4)

        body = ttk.Frame(self, style="Root.TFrame")
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        settings = ttk.Frame(body, style="Panel.TFrame", padding=12, width=250)
        settings.pack(side=tk.LEFT, fill=tk.Y)
        settings.pack_propagate(False)
        self._build_settings(settings)

        canvas_wrap = ttk.Frame(body, style="Root.TFrame")
        canvas_wrap.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        self.canvas = WorkCanvas(canvas_wrap, on_point=self._on_canvas_point, bg=self.bg_color)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        info = ttk.Frame(body, style="Panel.TFrame", padding=12, width=300)
        info.pack(side=tk.RIGHT, fill=tk.Y)
        info.pack_propagate(False)
        self._build_info(info)

        status = tk.Label(
            self,
            text="ЛКМ — новый отрезок (две точки) · Удалить — последний объект · ПКМ — панорама · колесо — масштаб",
            bg="#d9d2c3",
            fg="#3d3a32",
            font=("Segoe UI", 9),
            anchor="w",
            padx=12,
            pady=4,
        )
        status.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_settings(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Панель настроек", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        ttk.Label(parent, text="Система координат").pack(anchor="w")
        ttk.Radiobutton(
            parent, text="Декартова (x, y)", variable=self.coord_mode, value="cartesian", command=self._refresh_fields_mode
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            parent,
            text="Полярная (r, θ)",
            variable=self.coord_mode,
            value="polar",
            command=self._refresh_fields_mode,
        ).pack(anchor="w", pady=2)
        ttk.Label(
            parent,
            text="В полярном режиме P1 задается как (x, y),\nа P2 — радиусом и углом от P1.",
            style="Hint.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(parent, text="Единицы углов").pack(anchor="w")
        ttk.Radiobutton(
            parent, text="Градусы", variable=self.angle_mode, value="degrees", command=self._on_angle_mode
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            parent, text="Радианы", variable=self.angle_mode, value="radians", command=self._on_angle_mode
        ).pack(anchor="w", pady=2)

        ttk.Separator(parent).pack(fill=tk.X, pady=12)
        ttk.Label(parent, text="Шаг сетки").pack(anchor="w")
        step_row = ttk.Frame(parent, style="Panel.TFrame")
        step_row.pack(fill=tk.X, pady=4)
        ttk.Entry(step_row, textvariable=self.grid_step, width=10).pack(side=tk.LEFT)
        ttk.Button(step_row, text="Применить", command=self._apply_grid).pack(side=tk.LEFT, padx=6)

        ttk.Separator(parent).pack(fill=tk.X, pady=12)
        ttk.Label(parent, text="Координаты точек", style="Title.TLabel").pack(anchor="w", pady=(0, 8))

        self.lbl_p1a = ttk.Label(parent, text="P1 · x")
        self.lbl_p1a.pack(anchor="w")
        self.ent_p1a = ttk.Entry(parent)
        self.ent_p1a.pack(fill=tk.X, pady=(0, 6))
        self.lbl_p1b = ttk.Label(parent, text="P1 · y")
        self.lbl_p1b.pack(anchor="w")
        self.ent_p1b = ttk.Entry(parent)
        self.ent_p1b.pack(fill=tk.X, pady=(0, 10))

        self.lbl_p2a = ttk.Label(parent, text="P2 · x")
        self.lbl_p2a.pack(anchor="w")
        self.ent_p2a = ttk.Entry(parent)
        self.ent_p2a.pack(fill=tk.X, pady=(0, 6))
        self.lbl_p2b = ttk.Label(parent, text="P2 · y")
        self.lbl_p2b.pack(anchor="w")
        self.ent_p2b = ttk.Entry(parent)
        self.ent_p2b.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(parent, text="Построить отрезок", command=self.build_from_fields).pack(fill=tk.X, pady=(8, 0))
        for entry in (self.ent_p1a, self.ent_p1b, self.ent_p2a, self.ent_p2b):
            entry.bind("<Return>", lambda _e: self.build_from_fields())

        ttk.Label(
            parent,
            text="Каждое построение добавляет\nновый отрезок. «Удалить» снимает\nтолько последний объект.",
            style="Hint.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(8, 0))

    def _build_info(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Редактор отрезков", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        self.segment_list = tk.Listbox(
            parent,
            height=6,
            activestyle="dotbox",
            bg="#fffdf6",
            fg="#2c2a24",
            relief=tk.FLAT,
            exportselection=False,
            font=("Consolas", 10),
        )
        self.segment_list.pack(fill=tk.X)
        self.segment_list.bind("<<ListboxSelect>>", self._on_segment_select)

        ttk.Label(
            parent,
            text="Выберите отрезок и измените координаты его концов.",
            style="Hint.TLabel",
            justify="left",
        ).pack(anchor="w", pady=(6, 8))

        editor = ttk.Frame(parent, style="Panel.TFrame")
        editor.pack(fill=tk.X)
        self.edit_entries: dict[str, ttk.Entry] = {}
        for row, first, second in (
            ("P1", "x1", "y1"),
            ("P2", "x2", "y2"),
        ):
            ttk.Label(editor, text=row).pack(anchor="w", pady=(4, 0))
            line = ttk.Frame(editor, style="Panel.TFrame")
            line.pack(fill=tk.X, pady=(2, 4))
            for name in (first, second):
                cell = ttk.Frame(line, style="Panel.TFrame")
                cell.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
                ttk.Label(cell, text=name).pack(anchor="w")
                entry = ttk.Entry(cell, width=10)
                entry.pack(fill=tk.X)
                entry.bind("<Return>", lambda _e: self.apply_segment_edit())
                self.edit_entries[name] = entry

        ttk.Button(parent, text="Применить координаты", command=self.apply_segment_edit).pack(fill=tk.X, pady=(6, 10))

        ttk.Separator(parent).pack(fill=tk.X, pady=8)
        ttk.Label(parent, text="Информационная панель", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        self.info_text = tk.Text(
            parent,
            width=30,
            height=18,
            font=("Consolas", 10),
            bg="#fffdf6",
            fg="#2c2a24",
            relief=tk.FLAT,
            wrap=tk.WORD,
            padx=8,
            pady=8,
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)
        self.info_text.configure(state=tk.DISABLED)

    def _fmt_number(self, value: float) -> str:
        return f"{value:.4f}".rstrip("0").rstrip(".")

    def _segment_objects(self) -> list[SegmentShape]:
        return [obj for obj in self._objects if isinstance(obj, SegmentShape)]

    def _selected_segment(self) -> Optional[SegmentShape]:
        if self._selected_index is None:
            return None
        object_index = self._selected_object_index()
        if object_index is None:
            return None
        shape = self._objects[object_index]
        if not isinstance(shape, SegmentShape):
            return None
        return shape

    def _selected_object_index(self) -> Optional[int]:
        if self._selected_index is None:
            return None

        segment_index = -1
        for object_index, obj in enumerate(self._objects):
            if isinstance(obj, SegmentShape):
                segment_index += 1
                if segment_index == self._selected_index:
                    return object_index
        return None

    def _refresh_segment_editor(self) -> None:
        segment_objects = self._segment_objects()
        if self._selected_index is not None and self._selected_index >= len(segment_objects):
            self._selected_index = len(segment_objects) - 1 if segment_objects else None

        self.segment_list.delete(0, tk.END)
        for i, shape in enumerate(segment_objects, start=1):
            self.segment_list.insert(tk.END, shape.title(i))

        if self._selected_index is not None:
            self.segment_list.selection_set(self._selected_index)
            self.segment_list.activate(self._selected_index)
            self.segment_list.see(self._selected_index)

        self._write_edit_fields()
        self.canvas.set_selected_index(self._selected_object_index())

    def _write_edit_fields(self) -> None:
        for entry in self.edit_entries.values():
            entry.delete(0, tk.END)

        if self._selected_index is None:
            return

        shape = self._selected_segment()
        if shape is None:
            return

        seg = shape.segment
        values = {
            "x1": seg.p1.x,
            "y1": seg.p1.y,
            "x2": seg.p2.x,
            "y2": seg.p2.y,
        }
        for name, value in values.items():
            self.edit_entries[name].insert(0, self._fmt_number(value))

    def _select_segment(self, index: Optional[int]) -> None:
        self._selected_index = index
        if index is None:
            self._p1 = None
            self._p2 = None
        else:
            shape = self._selected_segment()
            if shape is None:
                return
            self._p1, self._p2 = shape.p1, shape.p2
            self._awaiting = 0
            self._clear_entries()
            self._write_fields_from_points()
        self._refresh_segment_editor()
        self._update_info()

    def _on_segment_select(self, _event: tk.Event) -> None:
        selection = self.segment_list.curselection()
        if not selection:
            return
        self._select_segment(selection[0])

    def apply_segment_edit(self) -> None:
        if self._selected_index is None:
            messagebox.showinfo("Редактор отрезков", "Сначала выберите отрезок в списке.")
            return

        try:
            p1 = Point(
                self._parse_float(self.edit_entries["x1"], "x1"),
                self._parse_float(self.edit_entries["y1"], "y1"),
            )
            p2 = Point(
                self._parse_float(self.edit_entries["x2"], "x2"),
                self._parse_float(self.edit_entries["y2"], "y2"),
            )
        except ValueError as exc:
            messagebox.showerror("Редактор отрезков", str(exc))
            return

        shape = self._selected_segment()
        if shape is None:
            messagebox.showinfo("Редактор отрезков", "Выбранный отрезок не найден.")
            return

        shape.set_points(p1, p2)
        self._p1, self._p2 = p1, p2
        self._awaiting = 0
        self.canvas.set_objects(self._objects)
        self._clear_entries()
        self._write_fields_from_points()
        self._refresh_segment_editor()
        self._update_info()

    def _degrees(self) -> bool:
        return self.angle_mode.get() == "degrees"

    def _refresh_fields_mode(self) -> None:
        polar = self.coord_mode.get() == "polar"
        if polar:
            unit = "θ, °" if self._degrees() else "θ, рад"
            self.lbl_p1a.configure(text="P1 · x")
            self.lbl_p1b.configure(text="P1 · y")
            self.lbl_p2a.configure(text="P2 · r")
            self.lbl_p2b.configure(text=f"P2 · {unit}")
        else:
            self.lbl_p1a.configure(text="P1 · x")
            self.lbl_p1b.configure(text="P1 · y")
            self.lbl_p2a.configure(text="P2 · x")
            self.lbl_p2b.configure(text="P2 · y")
        self._write_fields_from_points()
        self._update_info()

    def _on_angle_mode(self) -> None:
        self._refresh_fields_mode()

    def _apply_grid(self) -> None:
        try:
            step = float(self.grid_step.get().replace(",", "."))
            if step <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Шаг сетки", "Введите положительное число.")
            return
        self.canvas.set_grid_step(step)

    def _pick_color(self, kind: str) -> None:
        current = {"segment": self.segment_color, "bg": self.bg_color, "grid": self.grid_color}[kind]
        chosen = colorchooser.askcolor(color=current, title="Выбор цвета")
        if not chosen or not chosen[1]:
            return
        color = chosen[1]
        if kind == "segment":
            self.segment_color = color
        elif kind == "bg":
            self.bg_color = color
        else:
            self.grid_color = color
        self.canvas.apply_colors(bg=self.bg_color, grid=self.grid_color, segment=self.segment_color)
        self.canvas.set_objects(self._objects)

    def start_segment(self) -> None:
        self._p1 = None
        self._p2 = None
        self._awaiting = 1
        self.canvas.set_preview(None)
        self.canvas.set_objects(self._objects)
        self._clear_entries()
        self._selected_index = None
        self._refresh_segment_editor()
        self._update_info()

    def delete_last(self) -> None:
        if self._awaiting != 0:
            self._p1 = None
            self._p2 = None
            self._awaiting = 0
            self.canvas.set_preview(None)
            self.canvas.set_objects(self._objects)
            self._sync_fields_to_last()
            self._refresh_segment_editor()
            self._update_info()
            return
        if not self._objects:
            return
        self._objects.pop()
        self.canvas.set_objects(self._objects)
        self._sync_fields_to_last()
        segment_objects = self._segment_objects()
        self._selected_index = len(segment_objects) - 1 if segment_objects else None
        self._refresh_segment_editor()
        self._update_info()

    def _sync_fields_to_last(self) -> None:
        self._clear_entries()
        segment_objects = self._segment_objects()
        if not segment_objects:
            self._p1 = None
            self._p2 = None
            return
        last = segment_objects[-1]
        self._p1, self._p2 = last.p1, last.p2
        self._write_fields_from_points()

    def _clear_entries(self) -> None:
        for e in (self.ent_p1a, self.ent_p1b, self.ent_p2a, self.ent_p2b):
            e.delete(0, tk.END)

    def _on_canvas_point(self, point: Point) -> None:
        if self._awaiting == 0:
            self._p1 = None
            self._p2 = None
            self._awaiting = 1
            self._clear_entries()
        if self._awaiting == 1:
            self._p1 = point
            self._awaiting = 2
            self.canvas.set_preview(point)
        else:
            self._p2 = point
            self._awaiting = 0
            self._objects.append(SegmentShape(Segment(self._p1, self._p2)))
            self._selected_index = len(self._segment_objects()) - 1
            self.canvas.set_objects(self._objects)
        self._write_fields_from_points()
        self._refresh_segment_editor()
        self._update_info()

    def _parse_float(self, widget: ttk.Entry, name: str) -> float:
        raw = widget.get().strip().replace(",", ".")
        if raw == "":
            raise ValueError(f"Не задано значение: {name}")
        return float(raw)

    def _point_from_fields(self, a: ttk.Entry, b: ttk.Entry, name: str) -> Point:
        va = self._parse_float(a, name)
        vb = self._parse_float(b, name)
        return Point(va, vb)

    def _points_from_fields(self) -> tuple[Point, Point]:
        p1 = self._point_from_fields(self.ent_p1a, self.ent_p1b, "P1")
        if self.coord_mode.get() == "cartesian":
            p2 = self._point_from_fields(self.ent_p2a, self.ent_p2b, "P2")
            return p1, p2

        radius = self._parse_float(self.ent_p2a, "P2 · r")
        angle = self._parse_float(self.ent_p2b, "P2 · θ")
        theta = to_radians(angle) if self._degrees() else angle
        direction = Point.from_polar(radius, theta)
        return p1, Point(p1.x + direction.x, p1.y + direction.y)

    def _apply_points(self, p1: Point, p2: Point) -> None:
        self._p1, self._p2 = p1, p2
        self._awaiting = 0
        self._objects.append(SegmentShape(Segment(p1, p2)))
        self._selected_index = len(self._segment_objects()) - 1
        self.canvas.set_objects(self._objects)
        self._refresh_segment_editor()
        self._update_info()

    def build_from_fields(self) -> None:
        try:
            p1, p2 = self._points_from_fields()
        except ValueError as exc:
            messagebox.showerror("Ввод координат", str(exc))
            return
        self._apply_points(p1, p2)

    def _write_fields_from_points(self) -> None:
        def fill(entry: ttk.Entry, value: Optional[float]) -> None:
            entry.delete(0, tk.END)
            if value is not None:
                entry.insert(0, f"{value:.4f}".rstrip("0").rstrip("."))

        def segment_polar_vals(p1: Point, p2: Point) -> tuple[float, float]:
            dx = p2.x - p1.x
            dy = p2.y - p1.y
            r = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            return r, math.degrees(th) if self._degrees() else th

        if self._p1 is None:
            return
        fill(self.ent_p1a, self._p1.x)
        fill(self.ent_p1b, self._p1.y)
        if self._p2 is not None:
            if self.coord_mode.get() == "cartesian":
                fill(self.ent_p2a, self._p2.x)
                fill(self.ent_p2b, self._p2.y)
            else:
                r, th = segment_polar_vals(self._p1, self._p2)
                fill(self.ent_p2a, r)
                fill(self.ent_p2b, th)

    def _fmt_point(self, p: Point) -> str:
        r, th = p.polar()
        ang = format_angle(th, self._degrees())
        return (
            f"  декартовы:  x = {p.x:.4f}, y = {p.y:.4f}\n"
            f"  полярные:   r = {r:.4f}, θ = {ang}"
        )

    def _update_info(self) -> None:
        segment_objects = self._segment_objects()
        lines = [f"Объектов на плоскости: {len(self._objects)}", ""]
        if segment_objects:
            lines.append("Список отрезков")
            for i, shape in enumerate(segment_objects, start=1):
                mark = " ← последний" if i == len(segment_objects) else ""
                if self._selected_index == i - 1:
                    mark += " ← выбран"
                lines.append(f"  {i}: |AB|={shape.length:.3f}{mark}")
            lines.append("")

        lines.append("Текущие координаты")
        lines.append("")
        if self._p1 is None:
            lines.append("P1: не задана")
        else:
            lines.append("P1:")
            lines.append(self._fmt_point(self._p1))
        lines.append("")
        if self._p2 is None:
            lines.append("P2: не задана")
        else:
            lines.append("P2:")
            lines.append(self._fmt_point(self._p2))
        lines.append("")
        if self._p1 is not None and self._p2 is not None:
            seg = Segment(self._p1, self._p2)
            lines.append("Параметры текущего отрезка")
            lines.append(f"  длина |P1P2| = {seg.length:.4f}")
            lines.append(f"  угол наклона = {format_angle(seg.inclination_rad, self._degrees())}")
            lines.append("")
            lines.append("Угол наклона отсчитывается от")
            lines.append("оси X против часовой стрелки.")
        elif self._awaiting == 1:
            lines.append("Режим построения: укажите P1")
        elif self._awaiting == 2:
            lines.append("Режим построения: укажите P2")
        else:
            lines.append("«Отрезок» или клик — новый объект.")
            lines.append("«Удалить» — снять последний.")

        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.configure(state=tk.DISABLED)


def run() -> None:
    app = SaprApp()
    app.mainloop()
