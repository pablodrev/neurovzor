"""
Роутер модуля диагностики дисплазии ТБС.
Регистрирует эндпоинты и связывает HTTP-запросы с сервисным слоем.
"""

from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException, status

from app.modules.hip_dysplasia.schemas import HipDysplasiaResponse
from app.modules.hip_dysplasia.service import HipDysplasiaService

router = APIRouter(prefix="/hip-dysplasia", tags=["Hip Dysplasia"])

_ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "application/dicom",
    "application/octet-stream",
}


def get_service(request: Request) -> HipDysplasiaService:
    """
    Dependency Injection: инициализирует сервис с уже загруженными моделями из app.state.
    Модели загружаются один раз в lifespan и переиспользуются.
    """
    return HipDysplasiaService(models=request.app.state.models)


@router.post(
    "/analyze",
    response_model=HipDysplasiaResponse,
    summary="Анализ рентгенограммы ТБС",
    description=(
        "Принимает рентгенограмму тазобедренного сустава (DICOM, PNG или JPG). "
        "Возвращает диагноз, геометрические измерения и данные для пошаговой визуализации."
    ),
    status_code=status.HTTP_200_OK,
)
async def analyze_hip_dysplasia(
    file: UploadFile = File(..., description="Рентгенограмма ТБС (DICOM / PNG / JPG)"),
    service: HipDysplasiaService = Depends(get_service),
) -> HipDysplasiaResponse:
    """
    **Эндпоинт анализа дисплазии ТБС.**

    - Принимает файл через multipart/form-data
    - Извлекает возраст из DICOM-метаданных (если DICOM)
    - Запускает YOLO → MedSAM → GeometryEngine → Classifier
    - Возвращает полный JSON с образовательными данными для фронтенда
    """
    # Валидация типа файла
    if file.content_type and file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Неподдерживаемый тип файла: {file.content_type}. "
                   f"Допустимые типы: {', '.join(_ALLOWED_CONTENT_TYPES)}",
        )

    result = await service.analyze(file)

    if result.status == "error":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.result.get("error", "Ошибка обработки изображения"),
        )

    # Приводим к типизированному ответу
    return HipDysplasiaResponse(
        module=result.module,
        status=result.status,
        result=result.result,
        educational_data=result.educational_data,
    )


@router.get(
    "/info",
    summary="Информация о модуле ТБС",
    tags=["Hip Dysplasia"],
)
async def module_info() -> dict:
    """Возвращает метаданные модуля: поддерживаемые форматы, описание алгоритма."""
    return {
        "module": "hip_dysplasia",
        "version": "2.0.0",
        "description": "Диагностика дисплазии тазобедренного сустава по рентгенограмме",
        "supported_formats": list(_ALLOWED_CONTENT_TYPES),
        "algorithm_steps": [
            "1. Проверка качества снимка (симметрия таза)",
            "2. Детекция анатомических структур (YOLO + MedSAM)",
            "3. Оценка ядра окостенения (норма с 3–6 мес)",
            "4. Линия Хильгенрейнера (через Y-образные хрящи)",
            "5. Линия Перкина + квадранты Омбредана",
            "6. Линии Шентона и Кальве",
            "7. Ацетабулярный угол (превышение нормы ≥5° = дисплазия)",
            "8. Дистанции h (норма 8–12 мм) и d (норма 10–15 мм)",
            "9. Шеечно-диафизарный угол (норма 140–150° у детей)",
            "10. Итоговая оценка: триада Путти",
        ],
        "acetabular_norms": {
            "0-1m":  "≈28°",
            "1-6m":  "≤27°",
            "6-12m": "20–25°",
            "1-2y":  "18–22°",
            "2-3y":  "≤20°",
            "3y+":   "≤18°",
        },
        "pathology_threshold": "Превышение нормального ацетабулярного угла на ≥5°",
        "distance_norms": {"h_mm": "8–12", "d_mm": "10–15"},
        "putti_triad": [
            "1. Увеличенный ацетабулярный угол",
            "2. Смещение проксимального конца бедра (изменение h и d)",
            "3. Задержка/отсутствие ядра окостенения",
        ],
    }
