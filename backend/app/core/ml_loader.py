"""
ML model loading utilities.
"""
import logging
import os
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)


def load_models():
    """
    Load ML models for diagnosis.
    Returns dict with loaded models.
    """
    models = {}
    
    # Load YOLO for segmentation
    try:
        from ultralytics import YOLO
        yolo_path = settings.YOLO_MODEL_PATH
        
        if os.path.exists(yolo_path):
            logger.info(f"Loading YOLO from {yolo_path}")
            yolo = YOLO(yolo_path)
            # Set to evaluation mode
            yolo.to(settings.DEVICE)
            models['yolo'] = yolo
            logger.info("✅ YOLO loaded")
        else:
            logger.warning(f"⚠️  YOLO model not found at {yolo_path}")
            
    except ImportError:
        logger.warning("⚠️  ultralytics not installed")
    except Exception as e:
        logger.error(f"❌ Failed to load YOLO: {e}")
    
    # Load MedSAM for segmentation (if available)
    # Currently placeholder - will be implemented when needed
    try:
        logger.info("MedSAM loading skipped (placeholder)")
        models['medsam'] = None
    except Exception as e:
        logger.error(f"❌ Failed to load MedSAM: {e}")
    
    return models
