"""
Абстрактный базовый класс для всех диагностических модулей платформы.

Паттерн «Плагин»: каждый новый диагноз (сколиоз, дисплазия, переломы)
реализует этот интерфейс и получает автоматическую регистрацию в системе.
"""

from abc import ABC, abstractmethod
from typing import Any

from fastapi import UploadFile
from pydantic import BaseModel


class DiagnosticResult(BaseModel):
    """Универсальная обёртка ответа для любого диагностического модуля."""

    module: str
    """Уникальный идентификатор модуля, например 'hip_dysplasia'."""

    status: str  # "success" | "error"

    result: dict[str, Any]
    """Итоговый клинический вывод: диагноз, уверенность."""

    educational_data: dict[str, Any]
    """
    Детальные данные для фронтенда:
    - masks: маски сегментации (RLE или полигоны)
    - keypoints: координаты ключевых точек
    - measurements: геометрические измерения и нормы
    """


class BaseDiagnosticModule(ABC):
    """
    Базовый класс для всех диагностических модулей.

    Для добавления нового диагноза (например, «сколиоз»):
    1. Создать папку app/modules/scoliosis/
    2. Унаследовать класс ScoliosisDiagnosticModule от BaseDiagnosticModule
    3. Реализовать методы module_name, supported_formats и analyze
    4. Зарегистрировать роутер в app/api/router.py
    """

    def __init__(self, models: dict[str, Any]) -> None:
        """
        :param models: словарь загруженных ML-моделей из app.state.models.
                       Каждый модуль берёт только нужные ему модели.
        """
        self.models = models

    @property
    @abstractmethod
    def module_name(self) -> str:
        """Уникальное имя модуля. Используется в ответе и логировании."""
        ...

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """
        Список поддерживаемых MIME-типов.
        Например: ['image/png', 'image/jpeg', 'application/dicom']
        """
        ...

    @abstractmethod
    async def analyze(self, file: UploadFile, **kwargs: Any) -> DiagnosticResult:
        """
        Основной метод анализа изображения.

        :param file: загруженный файл (DICOM, PNG, JPG).
        :param kwargs: дополнительные параметры (возраст пациента, сторона и т.д.).
        :return: DiagnosticResult с полными образовательными данными.
        """
        ...

    def _build_error_result(self, error_message: str) -> DiagnosticResult:
        """Вспомогательный метод: формирует стандартный ответ об ошибке."""
        return DiagnosticResult(
            module=self.module_name,
            status="error",
            result={"has_pathology": None, "confidence": 0.0, "error": error_message},
            educational_data={},
        )
