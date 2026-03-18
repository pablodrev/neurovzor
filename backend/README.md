# MedTech Diagnostic Platform

Модульная платформа диагностики патологий по рентген-снимкам.  
**Сегодня — дисплазия ТБС. Завтра — сколиоз. Послезавтра — всё остальное.**

---

## Архитектура

```
app/
├── main.py                        # Точка входа, lifespan, фабрика приложения
├── core/
│   ├── config.py                  # Конфигурация через pydantic-settings / .env
│   └── model_registry.py          # Загрузка ML-моделей при старте (lifespan)
├── api/
│   └── router.py                  # Центральный роутер — регистрирует модули
└── modules/
    ├── base.py                    # BaseDiagnosticModule — абстрактный контракт
    └── hip_dysplasia/
        ├── router.py              # FastAPI-роутер эндпоинтов
        ├── service.py             # Оркестратор ML-пайплайна
        ├── schemas.py             # Pydantic-схемы запроса/ответа
        ├── geometry.py            # GeometryEngine: линии, углы, дистанции
        ├── classifier.py          # AgeBasedClassifier: сравнение с нормами
        ├── dicom_utils.py         # Чтение DICOM, извлечение метаданных возраста
        └── mask_utils.py          # RLE-кодирование масок сегментации
```

### Паттерн «Модульный монолит»

Каждый диагностический модуль изолирован в своей директории и реализует
контракт `BaseDiagnosticModule`. Для добавления нового модуля (например, сколиоза):

1. Создать `app/modules/scoliosis/`
2. Унаследовать сервис от `BaseDiagnosticModule`
3. Добавить одну строку в `app/api/router.py`

---

## ML-пайплайн (модуль ТБС)

```
UploadFile (DICOM / PNG / JPG)
        │
        ▼
  [dicom_utils]  ←─── извлечение возраста пациента из DICOM-тегов
        │
        ▼
  [YOLO Detector] ──── локализация суставов → bbox
        │
        ▼
  [MedSAM Segmentator] ── маски костей (ilium, femur) → RLE
        │
        ▼
  [GeometryEngine] ─── линия Хильгенрейнера, Перкин, ацетабулярный индекс, h, d
        │
        ▼
  [AgeBasedClassifier] ── сравнение с нормами → диагноз + степень тяжести
        │
        ▼
  JSON Response (диагноз + ключевые точки + маски + уравнения линий)
```

---

## Быстрый старт

### Локально

```bash
# Клонировать и перейти в директорию
cd medtech_platform

# Установить зависимости
pip install -r requirements.txt

# Запустить (веса моделей опциональны — без них используются заглушки)
uvicorn app.main:app --reload --port 8000
```

### Docker

```bash
docker-compose up --build
```

### Конфигурация (.env)

```env
YOLO_HIP_WEIGHTS=weights/yolo_hip.pt
MEDSAM_WEIGHTS=weights/medsam.pth
DEVICE=cpu          # или cuda:0
YOLO_CONF_THRESHOLD=0.5
```

---

## API

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/health` | Проверка доступности |
| GET | `/api/v1/modules` | Список активных модулей |
| GET | `/api/v1/hip-dysplasia/info` | Метаданные модуля ТБС |
| POST | `/api/v1/hip-dysplasia/analyze` | Анализ рентгенограммы |

Интерактивная документация: `http://localhost:8000/docs`

### Пример запроса

```bash
curl -X POST http://localhost:8000/api/v1/hip-dysplasia/analyze \
  -F "file=@xray.dcm"
```

### Пример ответа

```json
{
  "module": "hip_dysplasia",
  "status": "success",
  "result": {
    "has_pathology": true,
    "confidence": 0.891,
    "side": "bilateral",
    "severity": "moderate"
  },
  "educational_data": {
    "masks": {
      "ilium": [1024, 512, 2048, 256],
      "femur": [3072, 128],
      "mask_shape": [512, 512]
    },
    "keypoints": {
      "hilgenreiner_points": [[128.0, 256.0], [384.0, 256.0]],
      "perkin_points": [[320.0, 200.0], [320.0, 400.0]],
      "acetabular_roof_points": [[128.0, 256.0], [320.0, 200.0]],
      "femoral_head_center": [230.0, 310.0]
    },
    "measurements": {
      "acetabular_index": 31.5,
      "normal_range": "≤25° (возраст: 6м)",
      "distance_h": 14.2,
      "distance_d": 90.0,
      "lines": [
        {"a": 0.0, "b": 1.0, "c": -256.0, "label": "hilgenreiner"},
        {"a": 1.0, "b": 0.0, "c": -320.0, "label": "perkin"},
        {"a": -0.28, "b": 0.96, "c": -210.0, "label": "acetabular_roof"}
      ]
    },
    "patient_age_months": 6
  }
}
```

---

## Тесты

```bash
pip install pytest pillow
pytest tests/ -v
```

---

## Добавление нового модуля (пример: сколиоз)

```python
# app/modules/scoliosis/service.py
from app.modules.base import BaseDiagnosticModule, DiagnosticResult

class ScoliosisDiagnosticModule(BaseDiagnosticModule):
    @property
    def module_name(self) -> str:
        return "scoliosis"

    @property
    def supported_formats(self) -> list[str]:
        return ["image/png", "image/jpeg", "application/dicom"]

    async def analyze(self, file, **kwargs) -> DiagnosticResult:
        # ... реализация пайплайна
        pass
```

```python
# app/api/router.py — добавить одну строку:
from app.modules.scoliosis.router import router as scoliosis_router
api_router.include_router(scoliosis_router)
```
