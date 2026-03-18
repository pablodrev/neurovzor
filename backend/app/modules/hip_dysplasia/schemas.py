"""
Pydantic-схемы для модуля диагностики дисплазии тазобедренного сустава (ТБС).

Структура ответа отражает алгоритм рентгенолога по шагам:
  Шаг 4  — линия Хильгенрейнера (Y-образные хрящи)
  Шаг 5  — линия Перкина/Омбредана + квадранты
  Шаг 6  — линии Шентона и Кальве
  Шаг 7  — ацетабулярный угол
  Шаг 8  — дистанции h и d (по Хильгенрейнеру)
  Шаг 9  — шеечно-диафизарный угол (ШДУ)
  Шаг 10 — итоговая оценка + триада Путти
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Базовые геометрические типы
# ---------------------------------------------------------------------------

class LineEquation(BaseModel):
    """Уравнение прямой ax + by + c = 0 для отрисовки на фронтенде."""
    a: float
    b: float
    c: float
    label: str = ""


# ---------------------------------------------------------------------------
# Маски сегментации (Шаг 2)
# ---------------------------------------------------------------------------

class SegmentationMasks(BaseModel):
    """
    RLE-маски всех анатомических структур, детектированных на снимке.
    RLE-формат: [start1, length1, start2, length2, ...]
    """
    ilium: list[int] = Field(default_factory=list, description="Подвздошная кость")
    femoral_head: list[int] = Field(default_factory=list, description="Головка бедренной кости")
    femoral_neck: list[int] = Field(default_factory=list, description="Шейка бедренной кости")
    femoral_shaft: list[int] = Field(default_factory=list, description="Диафиз бедренной кости")
    acetabulum: list[int] = Field(default_factory=list, description="Вертлужная впадина")
    obturator_foramen: list[int] = Field(default_factory=list, description="Запирательное отверстие")
    ossification_nucleus: list[int] = Field(
        default_factory=list,
        description="Ядро окостенения головки бедра (если появилось)",
    )
    mask_shape: list[int] = Field(
        default_factory=lambda: [512, 512],
        description="Размер маски [height, width]",
    )


# ---------------------------------------------------------------------------
# Ключевые анатомические точки (Шаги 2, 4, 5, 8)
# ---------------------------------------------------------------------------

class AnatomicalKeypoints(BaseModel):
    """
    Координаты ключевых точек, по которым строятся диагностические линии.
    Все координаты в пикселях исходного изображения.
    """
    # Для линии Хильгенрейнера (Шаг 4)
    triradiate_cartilage_left: Optional[list[float]] = Field(
        default=None, description="Левый Y-образный хрящ (дно вертлужной впадины) [x, y]"
    )
    triradiate_cartilage_right: Optional[list[float]] = Field(
        default=None, description="Правый Y-образный хрящ [x, y]"
    )

    # Для линии Перкина (Шаг 5)
    acetabular_edge_left: Optional[list[float]] = Field(
        default=None, description="Верхне-наружный край крыши вертлужной впадины слева [x, y]"
    )
    acetabular_edge_right: Optional[list[float]] = Field(
        default=None, description="Верхне-наружный край крыши вертлужной впадины справа [x, y]"
    )

    # Для ацетабулярного угла (Шаг 7)
    acetabular_roof_medial_left: Optional[list[float]] = Field(
        default=None, description="Медиальная точка крыши вертлужной впадины слева [x, y]"
    )
    acetabular_roof_medial_right: Optional[list[float]] = Field(
        default=None, description="Медиальная точка крыши вертлужной впадины справа [x, y]"
    )

    # Для дистанций h и d (Шаг 8)
    metaphysis_midpoint_left: Optional[list[float]] = Field(
        default=None,
        description="Середина метафизарной пластинки проксимального отдела бедра слева [x, y]",
    )
    metaphysis_midpoint_right: Optional[list[float]] = Field(
        default=None, description="То же, справа [x, y]"
    )
    acetabulum_floor_left: Optional[list[float]] = Field(
        default=None, description="Дно вертлужной впадины слева [x, y]"
    )
    acetabulum_floor_right: Optional[list[float]] = Field(
        default=None, description="Дно вертлужной впадины справа [x, y]"
    )

    # Головка и шейка для ШДУ и линий Шентона/Кальве (Шаги 6, 9)
    femoral_head_center_left: Optional[list[float]] = Field(
        default=None, description="Центр головки бедренной кости слева [x, y]"
    )
    femoral_head_center_right: Optional[list[float]] = Field(
        default=None, description="Центр головки бедренной кости справа [x, y]"
    )
    femoral_neck_axis_left: Optional[list[list[float]]] = Field(
        default=None, description="Две точки оси шейки бедра слева [[x1,y1],[x2,y2]]"
    )
    femoral_neck_axis_right: Optional[list[list[float]]] = Field(
        default=None, description="Две точки оси шейки бедра справа"
    )
    femoral_shaft_axis_left: Optional[list[list[float]]] = Field(
        default=None, description="Две точки оси диафиза бедра слева"
    )
    femoral_shaft_axis_right: Optional[list[list[float]]] = Field(
        default=None, description="Две точки оси диафиза бедра справа"
    )

    # Запирательное отверстие для линии Шентона (Шаг 6)
    obturator_foramen_upper_edge_left: Optional[list[float]] = Field(
        default=None, description="Верхний край запирательного отверстия слева [x, y]"
    )
    obturator_foramen_upper_edge_right: Optional[list[float]] = Field(
        default=None, description="Верхний край запирательного отверстия справа [x, y]"
    )


# ---------------------------------------------------------------------------
# Диагностические линии (Шаги 4–6)
# ---------------------------------------------------------------------------

class DiagnosticLines(BaseModel):
    """
    Уравнения всех диагностических линий для пошаговой отрисовки на фронтенде.
    Фронтенд рисует линии поверх рентгенограммы в указанном порядке (step).
    """
    hilgenreiner: Optional[LineEquation] = Field(
        default=None,
        description="Шаг 4: горизонтальная линия через Y-образные хрящи",
    )
    perkin_left: Optional[LineEquation] = Field(
        default=None,
        description="Шаг 5: вертикаль через верхне-наружный край вертлужной впадины (слева)",
    )
    perkin_right: Optional[LineEquation] = Field(
        default=None, description="Шаг 5: то же, справа"
    )
    acetabular_roof_left: Optional[LineEquation] = Field(
        default=None,
        description="Шаг 7: касательная к крыше вертлужной впадины слева",
    )
    acetabular_roof_right: Optional[LineEquation] = Field(
        default=None, description="Шаг 7: то же, справа"
    )
    shenton_left: Optional[LineEquation] = Field(
        default=None,
        description="Шаг 6: линия Шентона — дуга по нижнему краю шейки + верхний край запирательного отверстия (слева)",
    )
    shenton_right: Optional[LineEquation] = Field(
        default=None, description="Шаг 6: линия Шентона справа"
    )
    calve_left: Optional[LineEquation] = Field(
        default=None,
        description="Шаг 6: линия Кальве — дуга по наружному контуру подвздошной кости и шейке бедра (слева)",
    )
    calve_right: Optional[LineEquation] = Field(
        default=None, description="Шаг 6: линия Кальве справа"
    )


# ---------------------------------------------------------------------------
# Результаты измерений для каждой стороны (Шаги 7–9)
# ---------------------------------------------------------------------------

class SideMeasurements(BaseModel):
    """Числовые параметры одного тазобедренного сустава."""

    # Шаг 7: Ацетабулярный угол
    acetabular_index: Optional[float] = Field(
        default=None, description="Ацетабулярный индекс в градусах"
    )
    acetabular_index_normal_range: str = Field(
        default="", description="Возрастная норма ацетабулярного угла"
    )
    acetabular_index_pathological: Optional[bool] = Field(
        default=None,
        description="True если превышение нормы ≥5° (критерий дисплазии по шагу 7)",
    )

    # Шаг 8: Дистанции h и d
    distance_h_mm: Optional[float] = Field(
        default=None,
        description="h: расстояние от линии Хильгенрейнера до середины метафизарной пластинки (норма 8–12 мм)",
    )
    distance_d_mm: Optional[float] = Field(
        default=None,
        description="d: расстояние от дна вертлужной впадины до проекции h на горизонталь (норма 10–15 мм)",
    )
    distance_h_pathological: Optional[bool] = Field(
        default=None, description="True если h < 8 мм (смещение головки вверх)"
    )
    distance_d_pathological: Optional[bool] = Field(
        default=None, description="True если d > 15 мм (латеральное смещение)"
    )

    # Шаг 9: ШДУ
    neck_shaft_angle: Optional[float] = Field(
        default=None,
        description="Шеечно-диафизарный угол в градусах (норма дети 140–150°, взрослые 125–130°)",
    )
    neck_shaft_angle_pathological: Optional[bool] = Field(
        default=None,
        description="True если ШДУ превышает норму (вальгусная деформация при дисплазии)",
    )

    # Шаг 5: Квадрант Омбредана
    ombredanne_quadrant: Optional[Literal["inner_lower", "outer_lower", "outer_upper", "inner_upper"]] = Field(
        default=None,
        description=(
            "Положение ядра окостенения в квадрантах Омбредана: "
            "inner_lower=норма, outer_lower=подвывих, outer_upper=вывих"
        ),
    )

    # Шаг 6: Непрерывность дуг
    shenton_line_intact: Optional[bool] = Field(
        default=None,
        description="True если линия Шентона непрерывна (норма); False — признак смещения",
    )
    calve_line_intact: Optional[bool] = Field(
        default=None,
        description="True если линия Кальве непрерывна (норма)",
    )


# ---------------------------------------------------------------------------
# Оценка качества снимка (Шаг 1) и ядра окостенения (Шаг 3)
# ---------------------------------------------------------------------------

class XrayQuality(BaseModel):
    """Шаг 1: оценка симметричности и пригодности снимка для измерений."""
    is_symmetric: Optional[bool] = Field(
        default=None, description="True если таз симметричен (нет поворота пациента)"
    )
    quality_note: str = Field(
        default="",
        description="Предупреждение при неправильной укладке (влияет на точность углов и h)",
    )


class OssificationNucleus(BaseModel):
    """Шаг 3: оценка ядра окостенения головки бедра."""
    present_left: Optional[bool] = Field(default=None, description="Ядро окостенения слева присутствует")
    present_right: Optional[bool] = Field(default=None, description="Ядро окостенения справа присутствует")
    symmetric: Optional[bool] = Field(default=None, description="Ядра симметричны")
    age_appropriate: Optional[bool] = Field(
        default=None,
        description="Соответствует возрасту (ожидается с 3–6 мес, к 1 году должны быть чёткими)",
    )
    note: str = Field(default="", description="Клиническое примечание о ядре окостенения")


# ---------------------------------------------------------------------------
# Итоговая диагностика (Шаг 10)
# ---------------------------------------------------------------------------

class PuttiTriad(BaseModel):
    """
    Шаг 10: классическая триада Путти.
    Наличие всех трёх признаков — диагностический критерий дисплазии/вывиха.
    """
    excessive_acetabular_slope: Optional[bool] = Field(
        default=None,
        description="1) Избыточная скошенность крыши (увеличенный ацетабулярный угол)",
    )
    proximal_femur_displacement: Optional[bool] = Field(
        default=None,
        description="2) Смещение проксимального конца бедренной кости (изменение h и d)",
    )
    ossification_nucleus_delayed: Optional[bool] = Field(
        default=None,
        description="3) Задержка или отсутствие ядра окостенения головки бедра",
    )
    triad_score: int = Field(
        default=0,
        description="Количество положительных признаков триады (0–3)",
    )


class DiagnosisType(BaseModel):
    """Итоговый диагноз по результатам всех шагов."""
    diagnosis: Literal["normal", "dysplasia", "subluxation", "dislocation", "inconclusive"] = "inconclusive"
    severity: Optional[Literal["mild", "moderate", "severe"]] = None
    has_pathology: Optional[bool] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    side_affected: Literal["none", "left", "right", "bilateral"] = "none"
    putti_triad: PuttiTriad = Field(default_factory=PuttiTriad)
    clinical_notes: list[str] = Field(
        default_factory=list,
        description="Список клинических находок в порядке шагов алгоритма",
    )


# ---------------------------------------------------------------------------
# Полный набор образовательных данных
# ---------------------------------------------------------------------------

class EducationalData(BaseModel):
    """
    Полный набор данных для пошаговой визуализации на фронтенде.
    Каждое поле соответствует шагу алгоритма рентгенолога.
    """
    # Шаг 1
    xray_quality: XrayQuality = Field(default_factory=XrayQuality)
    # Шаг 2
    masks: SegmentationMasks = Field(default_factory=SegmentationMasks)
    keypoints: AnatomicalKeypoints = Field(default_factory=AnatomicalKeypoints)
    # Шаг 3
    ossification_nucleus: OssificationNucleus = Field(default_factory=OssificationNucleus)
    # Шаги 4–6: линии
    lines: DiagnosticLines = Field(default_factory=DiagnosticLines)
    # Шаги 7–9: измерения по сторонам
    measurements_left: SideMeasurements = Field(default_factory=SideMeasurements)
    measurements_right: SideMeasurements = Field(default_factory=SideMeasurements)
    # Метаданные пациента
    patient_age_months: Optional[int] = Field(
        default=None, description="Возраст пациента в месяцах (из DICOM)"
    )


# ---------------------------------------------------------------------------
# Финальный ответ API
# ---------------------------------------------------------------------------

class HipDysplasiaResponse(BaseModel):
    """Финальная схема ответа модуля ТБС."""
    module: str = "hip_dysplasia"
    status: str
    result: DiagnosisType
    educational_data: EducationalData
