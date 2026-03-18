"""
Lifespan context manager for loading and unloading ML models.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for FastAPI lifespan events.
    - On startup: Load ML models into app.state
    - On shutdown: Cleanup resources
    """
    # STARTUP
    logger.info("Starting up application...")
    
    try:
        # Import here to avoid circular imports
        from app.core.ml_loader import load_models
        logger.info("Loading ML models...")
        models = load_models()
        
        # Store models in app state
        app.state.models = models
        logger.info("✅ Models loaded successfully")
        logger.info(f"   - YOLO: {models.get('yolo', 'Not loaded')}")
        logger.info(f"   - MedSAM: {models.get('medsam', 'Not loaded')}")
        
    except Exception as e:
        logger.error(f"❌ Failed to load models: {e}")
        # Continue anyway (models will be loaded on-demand or give clear errors)
        app.state.models = {}
    
    yield
    
    # SHUTDOWN
    logger.info("Shutting down application...")
    # Cleanup if needed
    if hasattr(app.state, 'models'):
        app.state.models.clear()
    logger.info("✅ Shutdown complete")
