"""
Временное хранилище анализов пациентов (in-memory).
При перезагрузке контейнера теряется, но достаточно для dev/demo.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class PatientRecord(BaseModel):
    id: str
    name: str
    study: str
    date: str  # ISO format
    gender: Optional[str] = None
    age: Optional[str] = None  # e.g., "6 мес."
    landmarks: list = []
    results: dict = {}
    confidence: Optional[float] = None
    analysis_data: Optional[dict] = None  # Полный ответ от analyze


class PatientStore:
    """In-memory хранилище пациентов."""

    def __init__(self):
        self._patients: dict[str, PatientRecord] = {}
        self._last_id = 0

    def create(
        self,
        name: str,
        study: str,
        gender: Optional[str] = None,
        age: Optional[str] = None,
    ) -> PatientRecord:
        """Создает новый запись пациента."""
        self._last_id += 1
        patient_id = f"ПТ-2024-{self._last_id:04d}"

        patient = PatientRecord(
            id=patient_id,
            name=name,
            study=study,
            date=datetime.now().isoformat(),
            gender=gender,
            age=age,
        )
        self._patients[patient_id] = patient
        return patient

    def get(self, patient_id: str) -> Optional[PatientRecord]:
        """Получает пациента по ID."""
        return self._patients.get(patient_id)

    def list_all(self) -> list[PatientRecord]:
        """Возвращает список всех пациентов."""
        return list(self._patients.values())

    def update_analysis(self, patient_id: str, analysis_data: dict) -> bool:
        """Обновляет данные анализа для пациента."""
        if patient_id not in self._patients:
            return False

        patient = self._patients[patient_id]
        patient.analysis_data = analysis_data

        # Извлекаем основные данные для отображения
        if analysis_data.get("result"):
            patient.results = analysis_data["result"]
        if analysis_data.get("result"):
            patient.confidence = analysis_data["result"].get("confidence", 0)

        return True

    def clear(self):
        """Очищает хранилище."""
        self._patients.clear()
        self._last_id = 0


# Глобальный Store
_global_patient_store: Optional[PatientStore] = None


def get_patient_store() -> PatientStore:
    """Dependency injection для хранилища пациентов."""
    global _global_patient_store
    if _global_patient_store is None:
        _global_patient_store = PatientStore()
    return _global_patient_store
