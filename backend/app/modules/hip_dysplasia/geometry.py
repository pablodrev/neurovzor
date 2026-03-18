"""
GeometryEngine — математический движок, реализующий алгоритм рентгенолога.

Шаги алгоритма, реализованные здесь:
  Шаг 1: оценка симметричности таза
  Шаг 4: линия Хильгенрейнера (через Y-образные хрящи)
  Шаг 5: линия Перкина (вертикаль через верхне-наружный край впадины) + квадранты
  Шаг 6: линии Шентона и Кальве (непрерывность дуг)
  Шаг 7: ацетабулярный угол (Хильгенрейнер ∧ касательная к крыше впадины)
  Шаг 8: дистанции h (метафиз → линия Хильгенрейнера) и d (дно впадины → проекция)
  Шаг 9: шеечно-диафизарный угол (ШДУ)

Все координаты — в пикселях исходного изображения.
Физические расстояния (мм) требуют калибровочного коэффициента px_per_mm.
"""

import math
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np

from app.modules.hip_dysplasia.schemas import LineEquation


@dataclass
class Point:
    x: float
    y: float

    def as_list(self) -> list[float]:
        return [self.x, self.y]

    def distance_to(self, other: "Point") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass
class SideGeometry:
    """Результаты геометрических вычислений для одной стороны сустава."""

    # Шаг 7
    acetabular_index: Optional[float] = None
    acetabular_roof_line: Optional[LineEquation] = None
    acetabular_roof_points: list[list[float]] = field(default_factory=list)

    # Шаг 5
    perkin_line: Optional[LineEquation] = None
    perkin_point: Optional[list[float]] = None  # верхне-наружный край впадины
    ombredanne_quadrant: Optional[str] = None  # inner_lower / outer_lower / outer_upper

    # Шаг 6
    shenton_line: Optional[LineEquation] = None
    shenton_intact: Optional[bool] = None
    calve_line: Optional[LineEquation] = None
    calve_intact: Optional[bool] = None

    # Шаг 8
    distance_h_px: Optional[float] = None
    distance_d_px: Optional[float] = None
    distance_h_mm: Optional[float] = None
    distance_d_mm: Optional[float] = None

    # Шаг 9
    neck_shaft_angle: Optional[float] = None


@dataclass
class FullGeometryResult:
    """Полный результат геометрического анализа снимка."""

    # Шаг 1
    is_symmetric: Optional[bool] = None
    quality_note: str = ""

    # Шаг 4
    hilgenreiner_line: Optional[LineEquation] = None
    hilgenreiner_points: list[list[float]] = field(default_factory=list)

    # По сторонам
    left: SideGeometry = field(default_factory=SideGeometry)
    right: SideGeometry = field(default_factory=SideGeometry)


class GeometryEngine:
    """
    Реализует геометрические шаги алгоритма рентгенолога.

    Принимает словарь масок сегментированных костей и ключевые точки,
    возвращает FullGeometryResult для обеих сторон.

    px_per_mm: калибровочный коэффициент пикселей на мм.
    Если не известен — физические расстояния остаются None, пиксельные заполняются.
    """

    def __init__(self, px_per_mm: Optional[float] = None):
        self.px_per_mm = px_per_mm  # None → не конвертируем в мм

    def compute(self, masks: dict[str, np.ndarray]) -> FullGeometryResult:
        """
        Основной метод. Принимает словарь масок:
          masks["ilium_left"], masks["ilium_right"]
          masks["femoral_head_left"], masks["femoral_head_right"]
          masks["femoral_neck_left"], masks["femoral_neck_right"]
          masks["femoral_shaft_left"], masks["femoral_shaft_right"]
          masks["acetabulum_left"], masks["acetabulum_right"]
          masks["obturator_foramen_left"], masks["obturator_foramen_right"]
          masks["ossification_nucleus_left"], masks["ossification_nucleus_right"]  (опционально)
        """
        result = FullGeometryResult()

        # --- Шаг 4: Линия Хильгенрейнера ---
        # Строится по верхнему контуру Y-образных хрящей (дно вертлужных впадин)
        tc_left = self._find_triradiate_cartilage(masks.get("acetabulum_left"))
        tc_right = self._find_triradiate_cartilage(masks.get("acetabulum_right"))

        if tc_left and tc_right:
            result.hilgenreiner_line = self._line_through_two_points(tc_left, tc_right)
            result.hilgenreiner_points = [tc_left.as_list(), tc_right.as_list()]

            # Шаг 1: Симметричность — Y-хрящи должны быть на одной горизонтали
            y_diff = abs(tc_left.y - tc_right.y)
            height = masks.get("acetabulum_left", np.zeros((512, 512))).shape[0]
            # Допуск: не более 2% высоты изображения
            result.is_symmetric = y_diff < height * 0.02
            if not result.is_symmetric:
                result.quality_note = (
                    f"Возможный поворот пациента: Y-хрящи на разной высоте "
                    f"(Δy={y_diff:.1f}px). Углы и расстояние h могут быть недостоверны."
                )

        # --- По сторонам ---
        for side, tc, ilium_key, head_key, neck_key, shaft_key, acet_key, obtur_key in [
            ("left",  tc_left,
             "ilium_left", "femoral_head_left", "femoral_neck_left",
             "femoral_shaft_left", "acetabulum_left", "obturator_foramen_left"),
            ("right", tc_right,
             "ilium_right", "femoral_head_right", "femoral_neck_right",
             "femoral_shaft_right", "acetabulum_right", "obturator_foramen_right"),
        ]:
            side_result: SideGeometry = getattr(result, side)

            ilium_mask = masks.get(ilium_key)
            head_mask = masks.get(head_key)
            neck_mask = masks.get(neck_key)
            shaft_mask = masks.get(shaft_key)
            acet_mask = masks.get(acet_key)
            obtur_mask = masks.get(obtur_key)
            nucleus_mask = masks.get(f"ossification_nucleus_{side}")

            # Точки для расчётов
            acetabular_edge = self._find_acetabular_outer_edge(ilium_mask)
            acetabular_roof_medial = tc  # медиальная точка крыши = Y-хрящ
            femoral_head_center = self._find_mass_center(head_mask) if head_mask is not None else None
            metaphysis_mid = self._find_metaphysis_midpoint(neck_mask)
            acetabulum_floor = self._find_acetabulum_floor(acet_mask)
            neck_axis = self._find_bone_axis(neck_mask)
            shaft_axis = self._find_bone_axis(shaft_mask)
            obtur_upper = self._find_obturator_upper_edge(obtur_mask)
            nucleus_center = self._find_mass_center(nucleus_mask) if nucleus_mask is not None else None

            # Шаг 5: Линия Перкина
            if acetabular_edge:
                side_result.perkin_line = self._vertical_line(acetabular_edge)
                side_result.perkin_point = acetabular_edge.as_list()

                # Квадрант Омбредана по ядру окостенения (или головке)
                ref_point = nucleus_center or femoral_head_center
                if ref_point and result.hilgenreiner_line:
                    side_result.ombredanne_quadrant = self._compute_ombredanne_quadrant(
                        point=ref_point,
                        hilgenreiner=result.hilgenreiner_line,
                        perkin_x=acetabular_edge.x,
                    )

            # Шаг 7: Ацетабулярный угол
            if acetabular_edge and acetabular_roof_medial and result.hilgenreiner_line:
                roof_line = self._line_through_two_points(acetabular_roof_medial, acetabular_edge)
                side_result.acetabular_roof_line = roof_line
                side_result.acetabular_roof_points = [
                    acetabular_roof_medial.as_list(), acetabular_edge.as_list()
                ]
                side_result.acetabular_index = self._angle_between_lines(
                    result.hilgenreiner_line, roof_line
                )

            # Шаг 8: Дистанции h и d
            if metaphysis_mid and result.hilgenreiner_line:
                h_px = self._point_to_line_distance(metaphysis_mid, result.hilgenreiner_line)
                side_result.distance_h_px = h_px
                side_result.distance_h_mm = self._px_to_mm(h_px)

            if acetabulum_floor and result.hilgenreiner_line:
                # d = горизонтальное расстояние от дна впадины до метафиза
                # (проекции обеих точек на линию Хильгенрейнера)
                if metaphysis_mid:
                    d_px = abs(metaphysis_mid.x - acetabulum_floor.x)
                    side_result.distance_d_px = d_px
                    side_result.distance_d_mm = self._px_to_mm(d_px)

            # Шаг 9: Шеечно-диафизарный угол
            if neck_axis and shaft_axis:
                side_result.neck_shaft_angle = self._angle_between_lines(neck_axis, shaft_axis)

            # Шаг 6: Линии Шентона и Кальве (непрерывность оцениваем по смещению)
            if femoral_head_center and obtur_upper and result.hilgenreiner_line:
                side_result.shenton_line = self._line_through_two_points(
                    femoral_head_center, obtur_upper
                )
                # Непрерывность: ступенька появляется если головка смещена вверх
                # Упрощённая эвристика: h < 0 или голова выше линии Хильгенрейнера
                h_signed = self._signed_distance_above_line(
                    femoral_head_center, result.hilgenreiner_line
                )
                side_result.shenton_intact = h_signed >= 0

            if ilium_mask is not None and neck_axis:
                ilium_outer = self._find_outer_ilium_point(ilium_mask)
                if ilium_outer and femoral_head_center:
                    side_result.calve_line = self._line_through_two_points(
                        ilium_outer, femoral_head_center
                    )
                    # Линия Кальве нарушена при несоответствии суставных поверхностей
                    side_result.calve_intact = side_result.shenton_intact  # первое приближение

        return result

    # -----------------------------------------------------------------------
    # Детекция анатомических точек по маскам
    # -----------------------------------------------------------------------

    def _find_triradiate_cartilage(self, acetabulum_mask: Optional[np.ndarray]) -> Optional[Point]:
        """
        Шаг 4: Y-образный хрящ = дно вертлужной впадины.
        Берём нижнюю-медиальную точку маски вертлужной впадины.
        """
        if acetabulum_mask is None:
            return None
        coords = np.argwhere(acetabulum_mask > 0)
        if len(coords) == 0:
            return None
        # Нижняя точка (максимальный row = максимальный y)
        bottom_idx = coords[:, 0].argmax()
        y, x = coords[bottom_idx]
        return Point(float(x), float(y))

    def _find_acetabular_outer_edge(self, ilium_mask: Optional[np.ndarray]) -> Optional[Point]:
        """
        Шаг 5: верхне-наружный край крыши вертлужной впадины.
        Берём самую верхнюю и самую латеральную точку подвздошной кости.
        """
        if ilium_mask is None:
            return None
        coords = np.argwhere(ilium_mask > 0)
        if len(coords) == 0:
            return None
        # Верхняя четверть по y → из неё берём самую латеральную (max x)
        top_y = coords[:, 0].min()
        top_region = coords[coords[:, 0] < top_y + (coords[:, 0].max() - top_y) * 0.25]
        x = int(top_region[:, 1].max())
        y = int(top_region[top_region[:, 1] == x, 0].min())
        return Point(float(x), float(y))

    def _find_outer_ilium_point(self, ilium_mask: np.ndarray) -> Optional[Point]:
        """Наружный контур подвздошной кости (для линии Кальве)."""
        coords = np.argwhere(ilium_mask > 0)
        if len(coords) == 0:
            return None
        outer_idx = coords[:, 1].argmax()
        y, x = coords[outer_idx]
        return Point(float(x), float(y))

    def _find_metaphysis_midpoint(self, neck_mask: Optional[np.ndarray]) -> Optional[Point]:
        """
        Шаг 8: середина метафизарной пластинки проксимального отдела бедра.
        Аппроксимируем как нижнюю границу маски шейки бедра.
        """
        if neck_mask is None:
            return None
        coords = np.argwhere(neck_mask > 0)
        if len(coords) == 0:
            return None
        bottom_y = float(coords[:, 0].max())
        bottom_row = coords[coords[:, 0] == int(bottom_y)]
        mid_x = float(bottom_row[:, 1].mean())
        return Point(mid_x, bottom_y)

    def _find_acetabulum_floor(self, acet_mask: Optional[np.ndarray]) -> Optional[Point]:
        """Шаг 8: дно вертлужной впадины (медиальная нижняя точка маски)."""
        return self._find_triradiate_cartilage(acet_mask)  # та же логика

    def _find_obturator_upper_edge(self, obtur_mask: Optional[np.ndarray]) -> Optional[Point]:
        """Шаг 6: верхний край запирательного отверстия для линии Шентона."""
        if obtur_mask is None:
            return None
        coords = np.argwhere(obtur_mask > 0)
        if len(coords) == 0:
            return None
        top_idx = coords[:, 0].argmin()
        y, x = coords[top_idx]
        return Point(float(x), float(y))

    def _find_mass_center(self, mask: Optional[np.ndarray]) -> Optional[Point]:
        """Центр масс бинарной маски."""
        if mask is None:
            return None
        coords = np.argwhere(mask > 0)
        if len(coords) == 0:
            return None
        return Point(float(coords[:, 1].mean()), float(coords[:, 0].mean()))

    def _find_bone_axis(self, mask: Optional[np.ndarray]) -> Optional[LineEquation]:
        """
        Ось длинной кости (шейка или диафиз) методом PCA по маске.
        Возвращает уравнение прямой вдоль главной оси.
        """
        if mask is None:
            return None
        coords = np.argwhere(mask > 0).astype(float)
        if len(coords) < 5:
            return None
        # PCA: первый главный компонент = направление оси кости
        coords_centered = coords - coords.mean(axis=0)
        _, _, vt = np.linalg.svd(coords_centered, full_matrices=False)
        dy, dx = vt[0]  # coords в порядке (row, col) = (y, x)
        # Нормаль к оси: ax + by + c = 0
        cx, cy = coords.mean(axis=1)[1], coords.mean(axis=0)[0]  # центр
        # Прямая проходит через (cx, cy) с направлением (dx, dy)
        # Нормальная форма: dy*(x-cx) - dx*(y-cy) = 0  →  dy*x - dx*y + (dx*cy - dy*cx) = 0
        a, b, c = float(dy), float(-dx), float(dx * cy - dy * cx)
        norm = math.sqrt(a**2 + b**2) or 1.0
        return LineEquation(a=a / norm, b=b / norm, c=c / norm)

    # -----------------------------------------------------------------------
    # Геометрические примитивы
    # -----------------------------------------------------------------------

    @staticmethod
    def _line_through_two_points(p1: Point, p2: Point) -> LineEquation:
        """Уравнение прямой ax+by+c=0 через две точки (нормализованное)."""
        a = p2.y - p1.y
        b = p1.x - p2.x
        c = -(a * p1.x + b * p1.y)
        norm = math.sqrt(a**2 + b**2) or 1.0
        return LineEquation(a=a / norm, b=b / norm, c=c / norm)

    @staticmethod
    def _vertical_line(point: Point) -> LineEquation:
        """Вертикальная прямая x = point.x."""
        return LineEquation(a=1.0, b=0.0, c=-point.x)

    @staticmethod
    def _angle_between_lines(line1: LineEquation, line2: LineEquation) -> float:
        """Острый угол между двумя прямыми в градусах."""
        cos_theta = min(abs(line1.a * line2.a + line1.b * line2.b), 1.0)
        return math.degrees(math.acos(cos_theta))

    @staticmethod
    def _point_to_line_distance(point: Point, line: LineEquation) -> float:
        """Расстояние от точки до прямой (всегда ≥ 0)."""
        return abs(line.a * point.x + line.b * point.y + line.c)

    @staticmethod
    def _signed_distance_above_line(point: Point, line: LineEquation) -> float:
        """
        Знаковое расстояние: положительное — точка НИЖЕ линии (в системе Y↓ экрана).
        Для линии Хильгенрейнера: головка бедра должна быть ниже → значение > 0.
        """
        return line.a * point.x + line.b * point.y + line.c

    def _px_to_mm(self, px: Optional[float]) -> Optional[float]:
        """Конвертирует пиксели в мм, если задан калибровочный коэффициент."""
        if px is None or self.px_per_mm is None:
            return None
        return round(px / self.px_per_mm, 2)

    # -----------------------------------------------------------------------
    # Шаг 5: Квадрант Омбредана
    # -----------------------------------------------------------------------

    @staticmethod
    def _compute_ombredanne_quadrant(
        point: Point,
        hilgenreiner: LineEquation,
        perkin_x: float,
    ) -> str:
        """
        Определяет квадрант по расположению ядра окостенения (или головки бедра):
          inner_lower  — норма
          outer_lower  — подвывих
          outer_upper  — вывих
          inner_upper  — редкая патология
        """
        # Знак вертикали: положительный = выше линии Хильгенрейнера (в экранных координатах Y↓)
        signed = hilgenreiner.a * point.x + hilgenreiner.b * point.y + hilgenreiner.c
        is_above = signed < 0   # Y↓: меньший y = выше
        is_outer = point.x > perkin_x

        if not is_above and not is_outer:
            return "inner_lower"   # норма
        elif not is_above and is_outer:
            return "outer_lower"   # подвывих
        elif is_above and is_outer:
            return "outer_upper"   # вывих
        else:
            return "inner_upper"   # редко
