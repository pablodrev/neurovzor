"""
API routers for diagnosis endpoints.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


def get_models(app):
    """Dependency to get loaded models from app state."""
    def _get_models():
        return getattr(app, 'state', {}).get('models', {})
    return _get_models


async def analyze_hip_dysplasia(file: UploadFile = File(...), app=None):
    """Analyze hip X-ray for dysplasia."""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file
        image_data = await file.read()
        if not image_data:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # Get models
        models = getattr(app.state, 'models', {})
        
        # Create and run analysis
        from app.modules.hip_dysplasia import HipDysplasiaModule
        analyzer = HipDysplasiaModule(models)
        
        if not analyzer.validate_input(image_data):
            raise HTTPException(
                status_code=400, 
                detail="Invalid image format. Expected DICOM, JPG or PNG"
            )
        
        # Run analysis
        result = await analyzer.analyze(image_data)
        
        if result.get('status') == 'error':
            raise HTTPException(status_code=500, detail=result.get('error'))
        
        # Save to patient store
        from app.core.patient_store import patient_store
        patient_id = result.get('patient_id')
        patient_store.create_patient(patient_id)
        patient_store.add_result(patient_id, result)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def create_hip_dysplasia_router(app):
    """Create router for hip dysplasia analysis."""
    router = APIRouter(prefix="/hip-dysplasia", tags=["diagnosis"])
    
    @router.post("/analyze")
    async def analyze(file: UploadFile = File(...)):
        """Analyze X-ray for hip dysplasia."""
        return await analyze_hip_dysplasia(file, app)
    
    return router
