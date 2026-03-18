"""
Роутер для управления пациентами и результатами анализов.
Используется фронтендом для получения истории пациентов и результатов.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.patient_store import PatientStore, get_patient_store
from app.modules.hip_dysplasia.schemas import HipDysplasiaResponse

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get(
    "",
    response_model=list[dict],
    summary="Список всех пациентов",
)
async def list_patients(store: PatientStore = Depends(get_patient_store)):
    """Возвращает список пациентов с их базовой информацией."""
    patients = store.list_all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "study": p.study,
            "date": p.date,
            "gender": p.gender,
            "age": p.age,
        }
        for p in patients
    ]


@router.get(
    "/{patient_id}",
    response_model=dict,
    summary="Информация о пациенте",
)
async def get_patient(
    patient_id: str,
    store: PatientStore = Depends(get_patient_store),
):
    """Получает полную информацию о пациенте, включая результаты анализа."""
    patient = store.get(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент {patient_id} не найден",
        )

    return {
        "id": patient.id,
        "name": patient.name,
        "study": patient.study,
        "date": patient.date,
        "gender": patient.gender,
        "age": patient.age,
        "analysis_data": patient.analysis_data,
    }


@router.get(
    "/{patient_id}/landmarks",
    response_model=list[dict],
    summary="Ориентиры пациента",
)
async def get_landmarks(
    patient_id: str,
    store: PatientStore = Depends(get_patient_store),
):
    """Возвращает список ориентиров для визуализации."""
    patient = store.get(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент {patient_id} не найден",
        )

    # Извлекаем keypoints из анализа
    if patient.analysis_data and patient.analysis_data.get("educational_data"):
        edu_data = patient.analysis_data["educational_data"]
        keypoints = edu_data.get("keypoints", {})

        # Трансформируем в формат для UI
        landmarks = []
        categories = {
            "pelvis": [
                "triradiate_cartilage_left",
                "triradiate_cartilage_right",
                "acetabular_edge_left",
                "acetabular_edge_right",
                "acetabulum_floor_left",
                "acetabulum_floor_right",
            ],
            "femur": [
                "femoral_head_center_left",
                "femoral_head_center_right",
                "femoral_neck_axis_left",
                "femoral_neck_axis_right",
                "metaphysis_midpoint_left",
                "metaphysis_midpoint_right",
            ],
        }

        landmark_names = {
            "triradiate_cartilage_left": "Левый Y-образный хрящ",
            "triradiate_cartilage_right": "Правый Y-образный хрящ",
            "acetabular_edge_left": "Верхний край крыши вертл. впадины (слева)",
            "acetabular_edge_right": "Верхний край крыши вертл. впадины (справа)",
            "acetabulum_floor_left": "Дно вертлужной впадины (слева)",
            "acetabulum_floor_right": "Дно вертлужной впадины (справа)",
            "femoral_head_center_left": "Головка бедренной кости (слева)",
            "femoral_head_center_right": "Головка бедренной кости (справа)",
        }

        for category, field_names in categories.items():
            for field_name in field_names:
                if field_name in keypoints and keypoints[field_name]:
                    landmarks.append(
                        {
                            "id": field_name,
                            "category": category,
                            "name": landmark_names.get(field_name, field_name),
                            "checked": True,
                        }
                    )

        return landmarks

    return []


@router.get(
    "/{patient_id}/results",
    response_model=list[dict],
    summary="Результаты анализа",
)
async def get_results(
    patient_id: str,
    store: PatientStore = Depends(get_patient_store),
):
    """Возвращает результаты анализа (измерения, углы, диагноз)."""
    patient = store.get(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент {patient_id} не найден",
        )

    results = []

    if patient.analysis_data and patient.analysis_data.get("educational_data"):
        edu_data = patient.analysis_data["educational_data"]

        # Линии
        lines = edu_data.get("lines", {})
        for line_name, line_obj in lines.items():
            if line_obj:
                results.append(
                    {
                        "category": "lines",
                        "parameter": line_name.replace("_", " ").title(),
                        "left": "-",
                        "right": "-",
                        "normal": "-",
                        "status": "success",
                    }
                )

        # Углы (левая и правая стороны)
        measurements_left = edu_data.get("measurements_left", {})
        measurements_right = edu_data.get("measurements_right", {})

        if measurements_left.get("acetabular_index"):
            status_left = "success" if not measurements_left.get("acetabular_index_pathological") else "destructive"
            results.append(
                {
                    "category": "angles",
                    "parameter": "Ацетабулярный угол",
                    "left": f"{measurements_left['acetabular_index']:.1f}°",
                    "right": f"{measurements_right.get('acetabular_index', '-')}" if measurements_right.get('acetabular_index') else "-",
                    "normal": measurements_left.get("acetabular_index_normal_range", "-"),
                    "status": status_left,
                }
            )

        if measurements_left.get("distance_h_mm"):
            status_left = "success" if not measurements_left.get("distance_h_pathological") else "destructive"
            results.append(
                {
                    "category": "distances",
                    "parameter": "Расстояние h",
                    "left": f"{measurements_left['distance_h_mm']:.1f} мм",
                    "right": f"{measurements_right.get('distance_h_mm', '-')}" if measurements_right.get('distance_h_mm') else "-",
                    "normal": "8–12 мм",
                    "status": status_left,
                }
            )

    return results


@router.get(
    "/{patient_id}/confidence",
    response_model=dict,
    summary="Уверенность диагноза",
)
async def get_confidence(
    patient_id: str,
    store: PatientStore = Depends(get_patient_store),
):
    """Возвращает уверенность диагноза (0–1)."""
    patient = store.get(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент {patient_id} не найден",
        )

    confidence = 0.0
    if patient.analysis_data and patient.analysis_data.get("result"):
        confidence = patient.analysis_data["result"].get("confidence", 0.0)

    return {"value": confidence}
