"""
Конфигурация приложения через pydantic-settings.
Значения берутся из переменных окружения или .env файла.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_TITLE: str = "MedTech Diagnostic Platform"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # CORS — в продакшне заменить на конкретные домены
    CORS_ORIGINS: list[str] = ["*"]

    # Пути к весам ML-моделей (монтируются через volume в Docker)
    YOLO_HIP_WEIGHTS: str = "weights/yolo_hip.pt"
    MEDSAM_WEIGHTS: str = "weights/medsam.pth"

    # Параметры инференса
    YOLO_CONF_THRESHOLD: float = 0.5
    DEVICE: str = "cpu"  # "cuda:0" для GPU

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
