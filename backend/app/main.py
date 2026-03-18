"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.lifespan import lifespan
from app.api.diagnosis_router import create_hip_dysplasia_router
from app.api.patients_router import router as patients_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.API_TITLE,
        version=settings.API_VERSION,
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get(f"{settings.API_PREFIX}/health")
    async def health_check():
        """Health check endpoint."""
        models = getattr(app.state, 'models', {})
        return {
            "status": "ok",
            "version": settings.API_VERSION,
            "models_loaded": {
                "yolo": models.get('yolo') is not None,
                "medsam": models.get('medsam') is not None,
            }
        }
    
    # Register diagnosis routers
    hip_router = create_hip_dysplasia_router(app)
    app.include_router(hip_router, prefix=settings.API_PREFIX)
    
    # Register patient management routers
    app.include_router(patients_router, prefix=settings.API_PREFIX)
    
    logger.info("✅ FastAPI application configured")
    
    return app


# Create app instance
app = create_app()
