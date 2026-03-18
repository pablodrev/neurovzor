"""
Классификатор: реализует Шаг 10 алгоритма рентгенолога.

Объединяет результаты измерений в итоговый диагноз по трём критериям:
  1. Ацетабулярный угол (Шаг 7): норма при рождении ≈28°, 6 мес — 20–25°, 1 год — 18–22°
     Превышение нормы на ≥5° → признак дисплазии
  2. Дистанции h и d (Шаг 8): h норма 8–12 мм, d норма 10–15 мм
  3. Ядро окостенения (Шаг 3): задержка/асимметрия → признак патологии

Классическая триада Путти (все три = диагноз дисплазии/вывиха):
  1. Увеличенный ацетабулярный угол
  2. Смещение проксимального конца бедра (h↓ или d↑)
  3. Задержка ядра окостенения
"""

import math
import logging
from dataclasses import dataclass
from typing import Literal, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Нормы ацетабулярного угла по шагу 7 алгоритма
# Формат: (возраст_от_мес, возраст_до_мес, max_normal_angle, label_для_UI)
# ---------------------------------------------------------------------------
_ACETABULAR_NORMS: list[tuple[int, int, float, str]] = [
    (0,   1,  28.0, "≈28° (новорождённые)"),
    (1,   6,  27.0, "≤27°"),
    (6,   12, 25.0, "20–25°"),           # при рождении 28°, к 6 мес — до 25°
    (12,  24, 22.0, "18–22°"),
    (24,  36, 20.0, "≤20°"),
    (36,  999, 18.0, "≤18°"),
]
_DEFAULT_MAX_ACETABULAR = 25.0
_DEFAULT_ACETABULAR_LABEL = "≤25° (возраст не определён)"

# Порог патологии по шагу 7: превышение нормы ≥5°
_ACETABULAR_PATHOLOGY_THRESHOLD_DEG = 5.0

# Нормы для h (мм) по шагу 8
_H_NORM_MIN_MM = 8.0
_H_NORM_MAX_MM = 12.0

# Нормы для d (мм) по шагу 8
_D_NORM_MIN_MM = 10.0
_D_NORM_MAX_MM = 15.0

# Норма ШДУ по шагу 9 (дети)
_NSA_NORM_MIN = 140.0
_NSA_NORM_MAX = 150.0


@dataclass
class SideClassification:
    """Результат оценки одного сустава."""
    # Шаг 7
    acetabular_pathological: bool = False
    acetabular_deviation: float = 0.0   # превышение нормы в градусах

    # Шаг 8
    h_pathological: bool = False        # h < 8 мм (смещение вверх)
    d_pathological: bool = False        # d > 15 мм (латеральное смещение)

    # Шаг 9
    nsa_pathological: bool = False      # ШДУ > 150° у детей

    # Итог для этой стороны
    has_pathology: bool = False
    severity: Optional[str] = None     # mild / moderate / severe
    diagnosis: str = "inconclusive"    # normal / dysplasia / subluxation / dislocation


@dataclass
class FullClassification:
    """Итоговый результат по всему снимку."""
    left: SideClassification
    right: SideClassification

    # Триада Путти (Шаг 10)
    putti_1_acetabular: bool = False
    putti_2_displacement: bool = False
    putti_3_nucleus: bool = False
    putti_score: int = 0

    # Итоговый диагноз
    diagnosis: str = "inconclusive"
    has_pathology: Optional[bool] = None
    side_affected: str = "none"
    severity: Optional[str] = None
    confidence: float = 0.0
    clinical_notes: list[str] = None

    def __post_init__(self):
        if self.clinical_notes is None:
            self.clinical_notes = []


class AgeBasedClassifier:
    """
    Реализует Шаг 10 алгоритма — итоговую диагностическую оценку.
    """

    def classify(
        self,
        age_months: Optional[int],
        # Шаг 7
        acetabular_left: Optional[float] = None,
        acetabular_right: Optional[float] = None,
        # Шаг 8
        h_left_mm: Optional[float] = None,
        h_right_mm: Optional[float] = None,
        d_left_mm: Optional[float] = None,
        d_right_mm: Optional[float] = None,
        # Шаг 9
        nsa_left: Optional[float] = None,
        nsa_right: Optional[float] = None,
        # Шаг 3 (ядро окостенения)
        nucleus_present_left: Optional[bool] = None,
        nucleus_present_right: Optional[bool] = None,
        # Шаг 5 (квадранты)
        quadrant_left: Optional[str] = None,
        quadrant_right: Optional[str] = None,
        # Шаг 6 (непрерывность дуг)
        shenton_intact_left: Optional[bool] = None,
        shenton_intact_right: Optional[bool] = None,
    ) -> FullClassification:

        max_angle, angle_label = self._get_acetabular_norm(age_months)
        notes: list[str] = []

        left = self._classify_side(
            "левый",
            acetabular=acetabular_left,
            max_normal_angle=max_angle,
            h_mm=h_left_mm,
            d_mm=d_left_mm,
            nsa=nsa_left,
            quadrant=quadrant_left,
            shenton_intact=shenton_intact_left,
            notes=notes,
        )
        right = self._classify_side(
            "правый",
            acetabular=acetabular_right,
            max_normal_angle=max_angle,
            h_mm=h_right_mm,
            d_mm=d_right_mm,
            nsa=nsa_right,
            quadrant=quadrant_right,
            shenton_intact=shenton_intact_right,
            notes=notes,
        )

        # --- Триада Путти (Шаг 10) ---
        putti_1 = left.acetabular_pathological or right.acetabular_pathological
        putti_2 = left.h_pathological or right.h_pathological or left.d_pathological or right.d_pathological
        putti_3 = self._assess_nucleus_delay(
            nucleus_present_left, nucleus_present_right, age_months, notes
        )
        putti_score = sum([putti_1, putti_2, putti_3])

        # --- Квадрант → уточнение диагноза ---
        quadrant_diagnosis = self._quadrant_to_diagnosis(quadrant_left, quadrant_right, notes)

        # --- Финальный диагноз ---
        final_diagnosis, has_pathology, severity = self._final_diagnosis(
            left, right, putti_score, quadrant_diagnosis, notes
        )

        side_affected = self._compute_side(left.has_pathology, right.has_pathology)
        confidence = self._compute_confidence(putti_score, left, right)

        return FullClassification(
            left=left,
            right=right,
            putti_1_acetabular=putti_1,
            putti_2_displacement=putti_2,
            putti_3_nucleus=putti_3,
            putti_score=putti_score,
            diagnosis=final_diagnosis,
            has_pathology=has_pathology,
            side_affected=side_affected,
            severity=severity,
            confidence=confidence,
            clinical_notes=notes,
        )

    # -----------------------------------------------------------------------
    # Оценка одной стороны
    # -----------------------------------------------------------------------

    def _classify_side(
        self,
        side_name: str,
        acetabular: Optional[float],
        max_normal_angle: float,
        h_mm: Optional[float],
        d_mm: Optional[float],
        nsa: Optional[float],
        quadrant: Optional[str],
        shenton_intact: Optional[bool],
        notes: list[str],
    ) -> SideClassification:
        result = SideClassification()

        # Шаг 7: ацетабулярный угол
        if acetabular is not None:
            deviation = acetabular - max_normal_angle
            result.acetabular_deviation = deviation
            if deviation >= _ACETABULAR_PATHOLOGY_THRESHOLD_DEG:
                result.acetabular_pathological = True
                notes.append(
                    f"[Шаг 7] {side_name}: ацетабулярный угол {acetabular:.1f}° "
                    f"превышает норму на {deviation:.1f}° (≥5° = дисплазия)"
                )

        # Шаг 8: дистанции h и d
        if h_mm is not None:
            if h_mm < _H_NORM_MIN_MM:
                result.h_pathological = True
                notes.append(
                    f"[Шаг 8] {side_name}: h={h_mm:.1f} мм < нормы 8–12 мм "
                    f"(смещение головки вверх)"
                )
            elif h_mm > _H_NORM_MAX_MM:
                notes.append(f"[Шаг 8] {side_name}: h={h_mm:.1f} мм в норме")

        if d_mm is not None:
            if d_mm > _D_NORM_MAX_MM:
                result.d_pathological = True
                notes.append(
                    f"[Шаг 8] {side_name}: d={d_mm:.1f} мм > нормы 10–15 мм "
                    f"(латеральное смещение)"
                )

        # Шаг 9: ШДУ
        if nsa is not None and nsa > _NSA_NORM_MAX:
            result.nsa_pathological = True
            notes.append(
                f"[Шаг 9] {side_name}: ШДУ={nsa:.1f}° > 150° "
                f"(вальгусная деформация, характерна для дисплазии)"
            )

        # Шаг 6: линии Шентона/Кальве
        if shenton_intact is False:
            notes.append(
                f"[Шаг 6] {side_name}: линия Шентона прервана "
                f"(«ступенька» — признак смещения бедренной кости)"
            )

        result.has_pathology = any([
            result.acetabular_pathological,
            result.h_pathological,
            result.d_pathological,
            result.nsa_pathological,
            shenton_intact is False,
        ])

        if result.has_pathology:
            result.severity = self._grade_severity(result.acetabular_deviation)

        return result

    # -----------------------------------------------------------------------
    # Шаг 3: ядро окостенения
    # -----------------------------------------------------------------------

    @staticmethod
    def _assess_nucleus_delay(
        present_left: Optional[bool],
        present_right: Optional[bool],
        age_months: Optional[int],
        notes: list[str],
    ) -> bool:
        """Задержка ядра окостенения = третий признак триады Путти."""
        if age_months is None or (present_left is None and present_right is None):
            return False

        # Ядра ожидаются с 3–6 мес, к 1 году должны быть чёткими
        expected = age_months >= 3

        if expected:
            missing = (present_left is False) or (present_right is False)
            asymmetric = (present_left is not None and present_right is not None
                          and present_left != present_right)
            if missing:
                notes.append(
                    f"[Шаг 3] Ядро окостенения отсутствует (возраст {age_months} мес, "
                    f"ожидается с 3–6 мес) — признак Путти №3"
                )
                return True
            if asymmetric:
                notes.append(
                    f"[Шаг 3] Ядра окостенения асимметричны "
                    f"(левое={'есть' if present_left else 'нет'}, "
                    f"правое={'есть' if present_right else 'нет'})"
                )
                return True
        return False

    # -----------------------------------------------------------------------
    # Шаг 5: квадранты → подвывих / вывих
    # -----------------------------------------------------------------------

    @staticmethod
    def _quadrant_to_diagnosis(
        quadrant_left: Optional[str],
        quadrant_right: Optional[str],
        notes: list[str],
    ) -> str:
        """Уточняет диагноз по положению ядра в квадрантах Омбредана."""
        worst = "normal"
        mapping = {
            "inner_lower": "normal",
            "outer_lower": "subluxation",
            "outer_upper": "dislocation",
            "inner_upper": "dysplasia",
        }
        for side_name, q in [("левый", quadrant_left), ("правый", quadrant_right)]:
            if q and q != "inner_lower":
                diag = mapping.get(q, "dysplasia")
                notes.append(
                    f"[Шаг 5] {side_name}: ядро в квадранте '{q}' "
                    f"→ {diag}"
                )
                if diag == "dislocation":
                    worst = "dislocation"
                elif diag == "subluxation" and worst != "dislocation":
                    worst = "subluxation"
                elif worst == "normal":
                    worst = "dysplasia"
        return worst

    # -----------------------------------------------------------------------
    # Итоговый диагноз
    # -----------------------------------------------------------------------

    @staticmethod
    def _final_diagnosis(
        left: SideClassification,
        right: SideClassification,
        putti_score: int,
        quadrant_diagnosis: str,
        notes: list[str],
    ) -> tuple[str, Optional[bool], Optional[str]]:
        """
        Шаг 10: объединяет все признаки.
        Квадранты Омбредана имеют приоритет над остальными критериями.
        """
        if quadrant_diagnosis == "dislocation":
            notes.append("[Шаг 10] Диагноз: врождённый вывих бедра (по квадранту Омбредана)")
            return "dislocation", True, "severe"

        if quadrant_diagnosis == "subluxation":
            notes.append("[Шаг 10] Диагноз: подвывих (по квадранту Омбредана)")
            return "subluxation", True, "moderate"

        if putti_score >= 2:
            severity = "severe" if putti_score == 3 else "moderate"
            notes.append(
                f"[Шаг 10] Триада Путти: {putti_score}/3 признаков → дисплазия ({severity})"
            )
            return "dysplasia", True, severity

        has_any = left.has_pathology or right.has_pathology
        if has_any:
            severity = (
                left.severity or right.severity or
                ("mild" if (left.acetabular_deviation or 0) + (right.acetabular_deviation or 0) < 10 else "moderate")
            )
            notes.append(f"[Шаг 10] Признаки дисплазии ({severity}) без полной триады Путти")
            return "dysplasia", True, severity

        notes.append("[Шаг 10] Патологических признаков не выявлено")
        return "normal", False, None

    # -----------------------------------------------------------------------
    # Вспомогательные методы
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_acetabular_norm(age_months: Optional[int]) -> tuple[float, str]:
        if age_months is None:
            return _DEFAULT_MAX_ACETABULAR, _DEFAULT_ACETABULAR_LABEL
        for low, high, max_angle, label in _ACETABULAR_NORMS:
            if low <= age_months < high:
                return max_angle, label
        return _DEFAULT_MAX_ACETABULAR, _DEFAULT_ACETABULAR_LABEL

    @staticmethod
    def _grade_severity(deviation: float) -> str:
        """Степень по превышению нормального угла."""
        if deviation < 5:
            return "mild"
        elif deviation < 10:
            return "moderate"
        return "severe"

    @staticmethod
    def _compute_side(left_patho: bool, right_patho: bool) -> str:
        if left_patho and right_patho:
            return "bilateral"
        elif left_patho:
            return "left"
        elif right_patho:
            return "right"
        return "none"

    @staticmethod
    def _compute_confidence(putti_score: int, left: SideClassification, right: SideClassification) -> float:
        """Эвристическая уверенность: растёт с числом положительных признаков."""
        n_findings = sum([
            left.acetabular_pathological, right.acetabular_pathological,
            left.h_pathological, right.h_pathological,
            left.d_pathological, right.d_pathological,
            left.nsa_pathological, right.nsa_pathological,
        ])
        raw = 0.5 + putti_score * 0.12 + n_findings * 0.05
        return round(min(raw, 0.98), 3)
