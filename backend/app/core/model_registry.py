"""
Реестр ML-моделей: централизованная загрузка и управление жизненным циклом.
Модели загружаются один раз при старте и передаются через app.state.
"""

import logging
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Отвечает за загрузку всех ML-моделей платформы.
    При добавлении нового диагностического модуля — просто добавить метод _load_<name>.
    """

    async def load_all(self) -> dict[str, Any]:
        """Загружает все зарегистрированные модели. Возвращает словарь name -> model."""
        models: dict[str, Any] = {}

        models["yolo_hip"] = await self._load_yolo_hip()
        models["medsam"] = await self._load_medsam()

        return models

    async def unload_all(self, models: dict[str, Any]) -> None:
        """Освобождает ресурсы всех моделей (например, GPU-память)."""
        for name, model in models.items():
            try:
                # У ultralytics/torch нет явного unload, но можно удалить ссылку
                logger.info(f"[ModelRegistry] Выгружаем модель: {name}")
                del model
            except Exception as e:
                logger.warning(f"[ModelRegistry] Ошибка при выгрузке {name}: {e}")

    async def _load_yolo_hip(self) -> Any:
        """
        Загружает YOLOv8 для локализации суставов ТБС.
        Если веса не найдены — возвращает заглушку (удобно при разработке без GPU).
        """
        weights_path = Path(settings.YOLO_HIP_WEIGHTS)
        if not weights_path.exists():
            logger.warning(
                f"[ModelRegistry] Веса YOLO не найдены по пути {weights_path}. "
                "Используется заглушка MockYOLO."
            )
            return _MockYOLO()

        try:
            from ultralytics import YOLO  # type: ignore
            model = YOLO(str(weights_path))
            model.to(settings.DEVICE)
            logger.info(f"[ModelRegistry] YOLOv8 загружен с {weights_path}")
            return model
        except ImportError:
            logger.error("[ModelRegistry] ultralytics не установлен. Используется заглушка.")
            return _MockYOLO()

    async def _load_medsam(self) -> Any:
        """
        Загружает MedSAM для сегментации костей (подвздошная кость, бедренная кость).
        """
        weights_path = Path(settings.MEDSAM_WEIGHTS)
        if not weights_path.exists():
            logger.warning(
                f"[ModelRegistry] Веса MedSAM не найдены по пути {weights_path}. "
                "Используется заглушка MockMedSAM."
            )
            return _MockMedSAM()

        try:
            # Загрузка MedSAM через torch (реальная реализация зависит от репозитория)
            import torch  # type: ignore
            model = torch.load(str(weights_path), map_location=settings.DEVICE)
            model.eval()
            logger.info(f"[ModelRegistry] MedSAM загружен с {weights_path}")
            return model
        except ImportError:
            logger.error("[ModelRegistry] torch не установлен. Используется заглушка.")
            return _MockMedSAM()


# ---------------------------------------------------------------------------
# Заглушки для разработки / CI без GPU и весов моделей
# ---------------------------------------------------------------------------

class _MockYOLO:
    """Заглушка YOLOv8 — возвращает фиктивные bbox для тестирования пайплайна."""

    def predict(self, image, conf: float = 0.5, verbose: bool = False):
        logger.debug("[MockYOLO] predict() вызван (заглушка)")
        return [_MockYOLOResult()]


class _MockYOLOResult:
    """Имитирует результат ultralytics YOLO."""

    class _Boxes:
        # Два сустава: левый и правый (xyxy-формат, нормализованные координаты)
        xyxyn = [[0.2, 0.3, 0.4, 0.6], [0.6, 0.3, 0.8, 0.6]]
        conf = [0.92, 0.89]
        cls = [0, 0]

    boxes = _Boxes()


class _MockMedSAM:
    """Заглушка MedSAM — возвращает фиктивные маски в виде нулевых массивов."""

    def __call__(self, *args, **kwargs):
        import numpy as np
        logger.debug("[MockMedSAM] __call__() вызван (заглушка)")
        # Маски 512x512 (0/1)
        return {
            "ilium": np.zeros((512, 512), dtype=np.uint8),
            "femur": np.zeros((512, 512), dtype=np.uint8),
        }
