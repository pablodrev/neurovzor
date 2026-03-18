"""
Patient management API routers.
"""
from fastapi import APIRouter, HTTPException
from app.core.patient_store import patient_store

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/")
async def list_patients():
    """Get all patients."""
    return patient_store.get_all_patients()


@router.get("/{patient_id}")
async def get_patient(patient_id: str):
    """Get patient by ID."""
    patient = patient_store.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/{patient_id}/results")
async def get_patient_results(patient_id: str):
    """Get all analysis results for patient."""
    patient = patient_store.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient_store.get_results(patient_id)


@router.get("/{patient_id}/landmarks")
async def get_patient_landmarks(patient_id: str):
    """Get landmarks (keypoints) for latest analysis."""
    result = patient_store.get_latest_result(patient_id)
    if not result:
        raise HTTPException(status_code=404, detail="No analysis found")
    
    educational_data = result.get('educational_data', {})
    return {
        "keypoints": educational_data.get('keypoints', {}),
        "masks": educational_data.get('masks', {}),
    }


@router.get("/{patient_id}/confidence")
async def get_diagnosis_confidence(patient_id: str):
    """Get diagnosis confidence for latest analysis."""
    result = patient_store.get_latest_result(patient_id)
    if not result:
        raise HTTPException(status_code=404, detail="No analysis found")
    
    return result.get('result', {})
