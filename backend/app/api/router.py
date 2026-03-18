"""
Центральный роутер API.
Здесь подключаются роутеры всех диагностических модулей.
Чтобы добавить новый модуль (например, scoliosis):
  1. from app.modules.scoliosis.router import router as scoliosis_router
  2. api_router.include_router(scoliosis_router)
"""

from fastapi import APIRouter

from app.modules.hip_dysplasia.router import router as hip_dysplasia_router

api_router = APIRouter()

# --- Регистрация модулей ---
api_router.include_router(hip_dysplasia_router)
# api_router.include_router(scoliosis_router)   # будущий модуль
# api_router.include_router(fracture_router)    # будущий модуль


@api_router.get("/health", tags=["System"])
async def health_check() -> dict:
    """Проверка доступности сервиса."""
    return {"status": "ok"}


@api_router.get("/modules", tags=["System"])
async def list_modules() -> dict:
    """Список зарегистрированных диагностических модулей."""
    return {
        "modules": [
            {"name": "hip_dysplasia", "path": "/api/v1/hip-dysplasia", "status": "active"},
            # {"name": "scoliosis", "path": "/api/v1/scoliosis", "status": "planned"},
        ]
    }
