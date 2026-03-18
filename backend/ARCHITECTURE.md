# Project structure documentation

## Backend Architecture

````
backend/
├── app/
│   ├── core/                      # 🔧 Ядро приложения
│   │   ├── config.py              # Конфигурация (settings, CORS, пути)
│   │   ├── lifespan.py            # Startup/shutdown хуки для загрузки ML моделей
│   │   ├── ml_loader.py           # Утилиты загрузки YOLO и MedSAM
│   │   ├── patient_store.py       # In-memory хранилище пациентов (можно заменить БД)
│   │   └── __init__.py
│   │
│   ├── api/                       # 🔗 API маршруты
│   │   ├── diagnosis_router.py    # Маршрут анализа (POST /api/v1/hip-dysplasia/analyze)
│   │   ├── patients_router.py     # Маршруты управления пациентами
│   │   └── __init__.py
│   │
│   ├── modules/                   # 🧩 Диагностические модули (plugin system)
│   │   ├── base.py                # Абстрактный базовый класс BaseDiagnosticModule
│   │   ├── hip_dysplasia/         # 🦵 Модуль анализа дисплазии ТБС
│   │   │   ├── module.py          # Логика анализа (сегментация, расчеты, диагноз)
│   │   │   ├── calculations.py    # 🔴 СЮДА ДОБАВИТЬ ВАШ КОД РАСЧЕТОВ!
│   │   │   └── __init__.py
│   │   │
│   │   # 📋 Следующие модули просто добавляются аналогично:
│   │   # ├── scoliosis/
│   │   # ├── knee_osteoarthritis/
│   │   # └── ...
│   │   └── __init__.py
│   │
│   ├── main.py                    # 🚀 FastAPI приложение + регистрация роутов
│   └── __init__.py
│
├── main.py                        # Entry point: uvicorn main:app --reload
├── requirements.txt               # Python зависимости
├── .env                           # Переменные окружения
└── README.md

## Расширяемость: Как добавить новый модуль?

### Пример: Добавить диагностику сколиоза

1. Создать папку `app/modules/scoliosis/`
2. Создать `scoliosis/module.py`:
```python
from app.modules.base import BaseDiagnosticModule

class ScoliosisModule(BaseDiagnosticModule):
    module_name = "scoliosis"

    async def analyze(self, image_data, patient_age=None, patient_sex=None):
        # Ваша логика анализа
        pass

    def validate_input(self, image_data):
        # Валидация изображения
        pass
````

3. Зарегистрировать в `app/main.py`:

```python
from app.modules.scoliosis import ScoliosisModule

@app.post("/api/v1/scoliosis/analyze")
async def analyze_scoliosis(file: UploadFile):
    analyzer = ScoliosisModule(app.state.models)
    return await analyzer.analyze(await file.read())
```

## Интеграция существующего кода расчетов

### Где разместить ваш код:

1. **Файл:** `app/modules/hip_dysplasia/calculations.py`
2. **Функция должна быть:**

```python
def compute_measurements(image_array, segmentation_results):
    """
    Вычисляет ключевые точки и линии.

    Возвращает:
    - measurements: {
        'left': {'acetabular_angle': 25.5, 'h': 12.3, 'd': 8.5, 'hilgenreiner_line': {...}},
        'right': {...}
      }
    - keypoints: {
        'left': [{'name': 'femoral_head_center', 'x': 100, 'y': 200}, ...],
        'right': [...]
      }
    """
```

3. **Использование в `module.py`:**

```python
from app.modules.hip_dysplasia.calculations import compute_measurements

# В методе analyze():
measurements, keypoints = compute_measurements(image_array, segmentation_results)
```

## API Endpoints

```
# Анализ рентгена
POST /api/v1/hip-dysplasia/analyze
  - file: multipart/form-data

# Управление пациентами
GET  /api/v1/patients
GET  /api/v1/patients/{patient_id}
GET  /api/v1/patients/{patient_id}/results
GET  /api/v1/patients/{patient_id}/landmarks
GET  /api/v1/patients/{patient_id}/confidence

# Health check
GET  /api/v1/health
```

## Запуск

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger docs доступна на: http://localhost:8000/docs

```

```
