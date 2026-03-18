"""
Сервис диагностики дисплазии ТБС.
Реализует BaseDiagnosticModule, оркеструя алгоритм рентгенолога (10 шагов):

  Шаг 1:  Оценка качества снимка (симметричность)
  Шаг 2:  Детекция ключевых структур (YOLO) + сегментация масок (MedSAM)
  Шаг 3:  Оценка ядра окостенения
  Шаг 4:  Линия Хильгенрейнера (через Y-образные хрящи)
  Шаг 5:  Линия Перкина + квадранты Омбредана
  Шаг 6:  Линии Шентона и Кальве
  Шаг 7:  Ацетабулярный угол
  Шаг 8:  Дистанции h и d
  Шаг 9:  Шеечно-диафизарный угол (ШДУ)
  Шаг 10: Итоговая оценка + триада Путти
"""

import logging
from typing import Any, Optional

import numpy as np
from fastapi import UploadFile

from app.modules.base import BaseDiagnosticModule, DiagnosticResult
from app.modules.hip_dysplasia.classifier import AgeBasedClassifier
from app.modules.hip_dysplasia.dicom_utils import extract_dicom_metadata
from app.modules.hip_dysplasia.geometry import GeometryEngine, FullGeometryResult
from app.modules.hip_dysplasia.mask_utils import mask_to_rle
from app.modules.hip_dysplasia.schemas import (
    AnatomicalKeypoints,
    DiagnosisType,
    DiagnosticLines,
    EducationalData,
    HipDysplasiaResponse,
    OssificationNucleus,
    PuttiTriad,
    SegmentationMasks,
    SideMeasurements,
    XrayQuality,
)

logger = logging.getLogger(__name__)

_SUPPORTED_FORMATS = [
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/dicom",
    "application/octet-stream",
]

# Классы сегментации, которые возвращает MedSAM
# Каждый класс соответствует одной анатомической структуре
_SEGMENTATION_CLASSES = [
    "ilium_left", "ilium_right",
    "femoral_head_left", "femoral_head_right",
    "femoral_neck_left", "femoral_neck_right",
    "femoral_shaft_left", "femoral_shaft_right",
    "acetabulum_left", "acetabulum_right",
    "obturator_foramen_left", "obturator_foramen_right",
    "ossification_nucleus_left", "ossification_nucleus_right",
]


class HipDysplasiaService(BaseDiagnosticModule):
    """
    Полный диагностический пайплайн для дисплазии тазобедренного сустава.
    Следует 10-шаговому алгоритму рентгенолога.
    """

    def __init__(self, models: dict[str, Any]) -> None:
        super().__init__(models)
        self._geometry = GeometryEngine()
        self._classifier = AgeBasedClassifier()

    @property
    def module_name(self) -> str:
        return "hip_dysplasia"

    @property
    def supported_formats(self) -> list[str]:
        return _SUPPORTED_FORMATS

    async def analyze(self, file: UploadFile, **kwargs: Any) -> DiagnosticResult:
        """Запускает полный 10-шаговый пайплайн анализа снимка ТБС."""
        try:
            raw_bytes = await file.read()

            # --- Загрузка изображения ---
            image_np, age_months = await self._load_image(raw_bytes, file.content_type)

            # --- Шаг 2: Детекция суставов (YOLO) ---
            joint_boxes = self._detect_joints(image_np)
            logger.info(f"[HipDysplasia] Найдено суставов: {len(joint_boxes)}")

            # --- Шаг 2: Сегментация всех анатомических структур (MedSAM) ---
            masks = self._segment_structures(image_np, joint_boxes)

            # --- Шаги 1, 4–9: Геометрические расчёты ---
            # GeometryEngine принимает словарь масок по именам структур
            geo: FullGeometryResult = self._geometry.compute(masks)

            # --- Шаг 3: Оценка ядра окостенения ---
            nucleus_info = self._assess_ossification_nucleus(masks, age_months)

            # --- Шаг 10: Классификация + триада Путти ---
            classification = self._classifier.classify(
                age_months=age_months,
                # Шаг 7
                acetabular_left=geo.left.acetabular_index,
                acetabular_right=geo.right.acetabular_index,
                # Шаг 8 (в мм, если калибровка доступна)
                h_left_mm=geo.left.distance_h_mm,
                h_right_mm=geo.right.distance_h_mm,
                d_left_mm=geo.left.distance_d_mm,
                d_right_mm=geo.right.distance_d_mm,
                # Шаг 9
                nsa_left=geo.left.neck_shaft_angle,
                nsa_right=geo.right.neck_shaft_angle,
                # Шаг 3
                nucleus_present_left=nucleus_info.present_left,
                nucleus_present_right=nucleus_info.present_right,
                # Шаг 5
                quadrant_left=geo.left.ombredanne_quadrant,
                quadrant_right=geo.right.ombredanne_quadrant,
                # Шаг 6
                shenton_intact_left=geo.left.shenton_intact,
                shenton_intact_right=geo.right.shenton_intact,
            )

            # --- Сборка ответа ---
            response = self._build_response(
                masks=masks,
                geo=geo,
                nucleus_info=nucleus_info,
                classification=classification,
                age_months=age_months,
            )

            return DiagnosticResult(
                module=self.module_name,
                status="success",
                result=response.result.model_dump(),
                educational_data=response.educational_data.model_dump(),
            )

        except Exception as e:
            logger.exception(f"[HipDysplasia] Ошибка в пайплайне: {e}")
            return self._build_error_result(str(e))

    # -----------------------------------------------------------------------
    # Шаг 2: Загрузка изображения
    # -----------------------------------------------------------------------

    async def _load_image(
        self, raw_bytes: bytes, content_type: Optional[str]
    ) -> tuple[np.ndarray, Optional[int]]:
        """DICOM → пиксели + возраст; PNG/JPG → только пиксели."""
        is_dicom = (
            content_type in ("application/dicom", "application/octet-stream")
            or raw_bytes[128:132] == b"DICM"
        )

        if is_dicom:
            metadata = extract_dicom_metadata(raw_bytes)
            pixel_array = metadata.get("pixel_array")
            if pixel_array is None:
                raise ValueError("Не удалось извлечь пиксельные данные из DICOM")
            return self._ensure_rgb(pixel_array), metadata.get("age_months")

        import cv2  # type: ignore
        nparr = np.frombuffer(raw_bytes, np.uint8)
        image_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image_np is None:
            raise ValueError("Не удалось декодировать изображение")
        return image_np, None

    @staticmethod
    def _ensure_rgb(array: np.ndarray) -> np.ndarray:
        import cv2  # type: ignore
        if array.ndim == 2:
            return cv2.cvtColor(array, cv2.COLOR_GRAY2BGR)
        return array

    # -----------------------------------------------------------------------
    # Шаг 2: YOLO-детекция
    # -----------------------------------------------------------------------

    def _detect_joints(self, image: np.ndarray) -> list[list[float]]:
        """Детекция суставов YOLO → список bbox [[x1,y1,x2,y2], ...]."""
        yolo = self.models.get("yolo_hip")
        if yolo is None:
            return []

        from app.core.config import settings
        results = yolo.predict(image, conf=settings.YOLO_CONF_THRESHOLD, verbose=False)

        boxes = []
        if results and hasattr(results[0], "boxes"):
            h, w = image.shape[:2]
            for box in results[0].boxes.xyxyn:
                x1, y1, x2, y2 = box
                boxes.append([float(x1) * w, float(y1) * h, float(x2) * w, float(y2) * h])
        return boxes

    # -----------------------------------------------------------------------
    # Шаг 2: MedSAM-сегментация всех анатомических структур
    # -----------------------------------------------------------------------

    def _segment_structures(
        self, image: np.ndarray, joint_boxes: list[list[float]]
    ) -> dict[str, np.ndarray]:
        """
        Сегментирует все 14 анатомических структур.
        MedSAM принимает изображение + bbox и возвращает маску.
        При отсутствии модели — нулевые маски (graceful degradation).
        """
        h, w = image.shape[:2]
        medsam = self.models.get("medsam")

        if medsam is None:
            logger.warning("[HipDysplasia] MedSAM не загружен, используются нулевые маски")
            return {cls: np.zeros((h, w), dtype=np.uint8) for cls in _SEGMENTATION_CLASSES}

        # В реальной реализации: для каждой структуры передаём bbox-подсказку
        masks = medsam(image=image, boxes=joint_boxes)

        # Убеждаемся что все ожидаемые ключи присутствуют
        for cls in _SEGMENTATION_CLASSES:
            if cls not in masks:
                masks[cls] = np.zeros((h, w), dtype=np.uint8)

        return masks

    # -----------------------------------------------------------------------
    # Шаг 3: Ядро окостенения
    # -----------------------------------------------------------------------

    def _assess_ossification_nucleus(
        self, masks: dict[str, np.ndarray], age_months: Optional[int]
    ) -> OssificationNucleus:
        """Шаг 3: определяет наличие и симметричность ядер окостенения."""
        nucleus_l = masks.get("ossification_nucleus_left", np.zeros((1, 1), dtype=np.uint8))
        nucleus_r = masks.get("ossification_nucleus_right", np.zeros((1, 1), dtype=np.uint8))

        present_l = bool(nucleus_l.any())
        present_r = bool(nucleus_r.any())
        symmetric = present_l == present_r

        # Клиническое примечание
        note = ""
        if age_months is not None and age_months >= 3:
            if not present_l or not present_r:
                note = (
                    f"Ядро окостенения отсутствует (возраст {age_months} мес). "
                    "Ожидается с 3–6 мес. Может сопровождать дисплазию."
                )
            elif not symmetric:
                note = "Ядра окостенения асимметричны — требуется клиническая оценка."

        age_appropriate = None
        if age_months is not None:
            if age_months < 3:
                age_appropriate = True  # до 3 мес ядра ещё не ожидаются
            else:
                age_appropriate = present_l and present_r

        return OssificationNucleus(
            present_left=present_l,
            present_right=present_r,
            symmetric=symmetric,
            age_appropriate=age_appropriate,
            note=note,
        )

    # -----------------------------------------------------------------------
    # Сборка ответа
    # -----------------------------------------------------------------------

    def _build_response(
        self,
        masks: dict[str, np.ndarray],
        geo: FullGeometryResult,
        nucleus_info: OssificationNucleus,
        classification,
        age_months: Optional[int],
    ) -> HipDysplasiaResponse:
        """Собирает финальный объект ответа из результатов всех шагов."""

        # Кодируем маски в RLE
        mask_shape = list(next(iter(masks.values())).shape) if masks else [512, 512]
        seg_masks = SegmentationMasks(
            ilium=mask_to_rle(masks.get("ilium_left", np.zeros(mask_shape, dtype=np.uint8))),
            femoral_head=mask_to_rle(masks.get("femoral_head_left", np.zeros(mask_shape, dtype=np.uint8))),
            femoral_neck=mask_to_rle(masks.get("femoral_neck_left", np.zeros(mask_shape, dtype=np.uint8))),
            femoral_shaft=mask_to_rle(masks.get("femoral_shaft_left", np.zeros(mask_shape, dtype=np.uint8))),
            acetabulum=mask_to_rle(masks.get("acetabulum_left", np.zeros(mask_shape, dtype=np.uint8))),
            obturator_foramen=mask_to_rle(masks.get("obturator_foramen_left", np.zeros(mask_shape, dtype=np.uint8))),
            ossification_nucleus=mask_to_rle(masks.get("ossification_nucleus_left", np.zeros(mask_shape, dtype=np.uint8))),
            mask_shape=mask_shape,
        )

        # Ключевые точки из геометрии
        keypoints = AnatomicalKeypoints(
            triradiate_cartilage_left=(
                geo.hilgenreiner_points[0] if len(geo.hilgenreiner_points) > 0 else None
            ),
            triradiate_cartilage_right=(
                geo.hilgenreiner_points[1] if len(geo.hilgenreiner_points) > 1 else None
            ),
            acetabular_edge_left=geo.left.perkin_point,
            acetabular_edge_right=geo.right.perkin_point,
            acetabular_roof_medial_left=(
                geo.left.acetabular_roof_points[0]
                if len(geo.left.acetabular_roof_points) > 0 else None
            ),
            acetabular_roof_medial_right=(
                geo.right.acetabular_roof_points[0]
                if len(geo.right.acetabular_roof_points) > 0 else None
            ),
        )

        # Диагностические линии
        lines = DiagnosticLines(
            hilgenreiner=geo.hilgenreiner_line,
            perkin_left=geo.left.perkin_line,
            perkin_right=geo.right.perkin_line,
            acetabular_roof_left=geo.left.acetabular_roof_line,
            acetabular_roof_right=geo.right.acetabular_roof_line,
            shenton_left=geo.left.shenton_line,
            shenton_right=geo.right.shenton_line,
            calve_left=geo.left.calve_line,
            calve_right=geo.right.calve_line,
        )

        # Измерения по сторонам
        max_angle, angle_label = self._classifier._get_acetabular_norm(age_months)

        def _side_measurements(side_geo, side_clf) -> SideMeasurements:
            return SideMeasurements(
                acetabular_index=side_geo.acetabular_index,
                acetabular_index_normal_range=angle_label,
                acetabular_index_pathological=side_clf.acetabular_pathological if side_clf else None,
                distance_h_mm=side_geo.distance_h_mm,
                distance_d_mm=side_geo.distance_d_mm,
                distance_h_pathological=side_clf.h_pathological if side_clf else None,
                distance_d_pathological=side_clf.d_pathological if side_clf else None,
                neck_shaft_angle=side_geo.neck_shaft_angle,
                neck_shaft_angle_pathological=side_clf.nsa_pathological if side_clf else None,
                ombredanne_quadrant=side_geo.ombredanne_quadrant,
                shenton_line_intact=side_geo.shenton_intact,
                calve_line_intact=side_geo.calve_intact,
            )

        meas_left = _side_measurements(geo.left, classification.left)
        meas_right = _side_measurements(geo.right, classification.right)

        # XRay quality (Шаг 1)
        xray_quality = XrayQuality(
            is_symmetric=geo.is_symmetric,
            quality_note=geo.quality_note,
        )

        educational_data = EducationalData(
            xray_quality=xray_quality,
            masks=seg_masks,
            keypoints=keypoints,
            ossification_nucleus=nucleus_info,
            lines=lines,
            measurements_left=meas_left,
            measurements_right=meas_right,
            patient_age_months=age_months,
        )

        # Итоговый диагноз
        result = DiagnosisType(
            diagnosis=classification.diagnosis,
            severity=classification.severity,
            has_pathology=classification.has_pathology,
            confidence=classification.confidence,
            side_affected=classification.side_affected,
            putti_triad=PuttiTriad(
                excessive_acetabular_slope=classification.putti_1_acetabular,
                proximal_femur_displacement=classification.putti_2_displacement,
                ossification_nucleus_delayed=classification.putti_3_nucleus,
                triad_score=classification.putti_score,
            ),
            clinical_notes=classification.clinical_notes,
        )

        return HipDysplasiaResponse(
            status="success",
            result=result,
            educational_data=educational_data,
        )
