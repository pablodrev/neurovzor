"""
Утилиты для работы с DICOM-файлами.
Извлекает метаданные (возраст пациента, дату рождения) и пиксельные данные.
"""

import io
import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# Теги DICOM для возраста пациента
_TAG_PATIENT_AGE = (0x0010, 0x1010)  # PatientAge, формат: "028Y", "006M", "003W"
_TAG_PATIENT_BIRTH_DATE = (0x0010, 0x0030)  # PatientBirthDate, формат: YYYYMMDD
_TAG_STUDY_DATE = (0x0008, 0x0020)  # StudyDate


def extract_dicom_metadata(dicom_bytes: bytes) -> dict:
    """
    Читает DICOM-файл и возвращает словарь метаданных.
    При ошибке чтения — возвращает пустой словарь (graceful degradation).

    :param dicom_bytes: сырые байты DICOM-файла
    :return: {"age_months": int | None, "pixel_array": np.ndarray | None, ...}
    """
    try:
        import pydicom  # type: ignore

        ds = pydicom.dcmread(io.BytesIO(dicom_bytes))
        return {
            "age_months": _parse_age_months(ds),
            "pixel_array": _extract_pixel_array(ds),
            "modality": getattr(ds, "Modality", None),
            "study_date": getattr(ds, "StudyDate", None),
        }
    except ImportError:
        logger.error("[DICOM] pydicom не установлен. Метаданные недоступны.")
        return {"age_months": None, "pixel_array": None}
    except Exception as e:
        logger.warning(f"[DICOM] Ошибка при чтении DICOM: {e}")
        return {"age_months": None, "pixel_array": None}


def _parse_age_months(ds) -> Optional[int]:
    """
    Парсит возраст пациента из DICOM-тегов.
    Форматы PatientAge: "028Y" (годы), "006M" (месяцы), "003W" (недели).
    Альтернатива: вычисление по PatientBirthDate + StudyDate.
    """
    import pydicom

    # Попытка 1: тег PatientAge
    patient_age = ds.get(_TAG_PATIENT_AGE)
    if patient_age:
        age_str = str(patient_age).strip()
        try:
            if age_str.endswith("Y"):
                return int(age_str[:-1]) * 12
            elif age_str.endswith("M"):
                return int(age_str[:-1])
            elif age_str.endswith("W"):
                return int(age_str[:-1]) // 4  # приближение
        except ValueError:
            pass

    # Попытка 2: вычисление из дат рождения и исследования
    birth_date = ds.get(_TAG_PATIENT_BIRTH_DATE)
    study_date = ds.get(_TAG_STUDY_DATE)
    if birth_date and study_date:
        try:
            from datetime import datetime

            bd = datetime.strptime(str(birth_date), "%Y%m%d")
            sd = datetime.strptime(str(study_date), "%Y%m%d")
            months = (sd.year - bd.year) * 12 + (sd.month - bd.month)
            return max(months, 0)
        except ValueError:
            pass

    return None


def _extract_pixel_array(ds) -> Optional[np.ndarray]:
    """Извлекает пиксельные данные из DICOM и нормализует в uint8."""
    try:
        pixel_array = ds.pixel_array.astype(np.float32)
        # Нормализация в диапазон 0-255
        p_min, p_max = pixel_array.min(), pixel_array.max()
        if p_max > p_min:
            pixel_array = (pixel_array - p_min) / (p_max - p_min) * 255.0
        return pixel_array.astype(np.uint8)
    except Exception as e:
        logger.warning(f"[DICOM] Не удалось извлечь пиксели: {e}")
        return None
