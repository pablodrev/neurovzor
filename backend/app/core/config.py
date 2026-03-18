"""
Core configuration for the medical diagnosis platform.
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Configuration
    API_PREFIX: str = "/api/v1"
    API_TITLE: str = "MedTech Hip Dysplasia Analyzer"
    API_VERSION: str = "1.0.0"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # ML Configuration
    YOLO_CONF_THRESHOLD: float = 0.5
    YOLO_IOU_THRESHOLD: float = 0.45
    DEVICE: str = "cpu"  # "cpu" or "cuda:0"
    
    # Model paths
    YOLO_MODEL_PATH: str = "weights/yolo26n-seg.pt"
    MEDSAM_MODEL_PATH: str = "weights/medsam.pth"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
