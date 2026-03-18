"""
MedTech платформа диагностики патологий по рентген-снимкам.
Точка входа приложения — регистрация модулей и lifespan-хук для ML-моделей.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.model_registry import ModelRegistry
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan-хук: загружает все ML-модели один раз при старте приложения
    и освобождает ресурсы при остановке.
    Модели хранятся в app.state, чтобы избежать повторной загрузки на каждый запрос.
    """
    registry = ModelRegistry()
    app.state.models = await registry.load_all()
    print(f"[lifespan] Загружено моделей: {list(app.state.models.keys())}")
    yield
    # Освобождаем GPU/CPU ресурсы при остановке
    await registry.unload_all(app.state.models)
    print("[lifespan] Все модели выгружены")


def create_app() -> FastAPI:
    """Фабрика приложения — удобно для тестирования."""
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        description="Модульная платформа МедТех-диагностики. Сегодня — ТБС, завтра — сколиоз.",
        lifespan=lifespan,
    )

    # CORS — для взаимодействия с фронтендом
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключаем центральный роутер (он сам подтягивает модули)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()
