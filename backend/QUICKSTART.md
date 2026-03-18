# 🚀 Backend MedTech Platform - Быстрый старт

## Структура проекта (Modular Monolith)

```
backend/
├── app/core/                  # Ядро: конфиг, ML загрузка, хранилище пациентов
├── app/api/                   # API маршруты
├── app/modules/
│   ├── base.py                # 🔴 BaseDiagnosticModule - абстрактный базовый класс
│   └── hip_dysplasia/         # 🦵 Модуль дисплазии ТБС
│       ├── module.py          # Основная логика
│       └── calculations.py    # 🔴 СЮДА поместить ваш код расчетов!
└── main.py                    # FastAPI приложение

```

## 1️⃣ Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

## 2️⃣ Скачать ML модели

```bash
# Создать папку для весов
mkdir -p weights

# Скачать YOLO26n-seg (например, с Hugging Face или Ultralytics Hub)
# Положить в: weights/yolo26n-seg.pt
```

## 3️⃣ Интегрировать ваш код расчетов

**Где:** `app/modules/hip_dysplasia/calculations.py`

```python
def compute_measurements(image_array, segmentation_results):
    """
    Вычисляет ключевые точки, линии и углы для дисплазии ТБС.

    Args:
        image_array: np.ndarray (H, W) - изображение
        segmentation_results: list - результаты YOLO сегментации
            [
                {'mask': polygon_coords, 'class': 'femur', 'confidence': 0.95},
                {'mask': polygon_coords, 'class': 'ilium', 'confidence': 0.92},
                {'mask': polygon_coords, 'class': 'pubis_ischium', 'confidence': 0.94},
            ]

    Returns:
        (measurements, keypoints) where:

        measurements = {
            'left': {
                'acetabular_angle': 25.5,  # Угол вертлужной впадины
                'h_distance': 12.3,         # CE angle расстояние h
                'd_distance': 8.5,          # Расстояние d
                'hilgenreiner_line': {
                    'p1': [x1, y1],
                    'p2': [x2, y2],
                    'equation': 'y = mx + b'
                }
            },
            'right': {...}
        }

        keypoints = {
            'left': [
                {'name': 'femoral_head_center', 'x': 100, 'y': 200, 'confidence': 0.95},
                {'name': 'acetabular_rim_superior', 'x': 150, 'y': 100, 'confidence': 0.92},
                ...
            ],
            'right': [...]
        }
    """
    # ВАШ КОД ЗДЕСЬ
    pass
```

**Как использовать в `module.py`:**

В методе `analyze()` замените:

```python
# This is the line in app/modules/hip_dysplasia/module.py ~line 65
measurements, keypoints = compute_measurements(image_array, segmentation_results)
```

Раскомментируйте и используйте:

```python
from app.modules.hip_dysplasia.calculations import compute_measurements
measurements, keypoints = compute_measurements(image_array, segmentation_results)
```

## 4️⃣ Запустить backend

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend готов на: http://localhost:8000

- API документация: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## 5️⃣ Запустить frontend (в другом терминале)

```bash
cd frontend
npm install
npm run dev
```

## 📡 API Endpoints

### Анализ рентгена

```bash
POST /api/v1/hip-dysplasia/analyze
Content-Type: multipart/form-data

Response:
{
  "patient_id": "PT-2024-0001",
  "module": "hip_dysplasia",
  "status": "success",
  "result": {
    "diagnosis": "normal|dysplasia|dislocation",
    "confidence": 0.95,
    "side_affected": "none|left|right|bilateral"
  },
  "educational_data": {
    "keypoints": {...},
    "masks": {...},
    "lines": {...},
    "measurements_left": {...},
    "measurements_right": {...}
  }
}
```

### Управление пациентами

```bash
GET /api/v1/patients                         # Все пациенты
GET /api/v1/patients/{patient_id}           # Один пациент
GET /api/v1/patients/{patient_id}/results   # Результаты анализа
GET /api/v1/patients/{patient_id}/landmarks # Ключевые точки
```

## 🔌 Расширяемость: Добавить новую диагностику за 3 шага

### Пример: Диагностика сколиоза

1. **Создать модуль:**

```bash
mkdir -p app/modules/scoliosis
```

2. **Создать `app/modules/scoliosis/module.py`:**

```python
from app.modules.base import BaseDiagnosticModule

class ScoliosisModule(BaseDiagnosticModule):
    module_name = "scoliosis"

    async def analyze(self, image_data, patient_age=None, patient_sex=None):
        # Ваша логика
        return {...}

    def validate_input(self, image_data):
        return True  # или ваша валидация
```

3. **Зарегистрировать в `app/main.py`:**

```python
from app.modules.scoliosis import ScoliosisModule

@app.post("/api/v1/scoliosis/analyze")
async def analyze_scoliosis(file):
    analyzer = ScoliosisModule(app.state.models)
    return await analyzer.analyze(await file.read())
```

## 🐛 Troubleshooting

### ModuleNotFoundError: No module named 'app'

```bash
# Убедитесь, что вы в папке backend
cd backend
# И запускаете из этой папки
uvicorn app.main:app --reload
```

### CORS Error в браузере

Проверьте `.env`:

```
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### YOLO not found

```bash
pip install ultralytics
# И скачайте модель в weights/yolo26n-seg.pt
```

## 📊 Workflow

1. Frontend отправляет DICOM/JPG на `/api/v1/hip-dysplasia/analyze`
2. Backend:
   - Загружает изображение (DICOM → pydicom, JPG/PNG → PIL)
   - Извлекает возраст из DICOM
   - Запускает YOLO сегментацию → masks
   - Вычисляет ключевые точки и углы → ваш код в calculations.py
   - Вычисляет диагноз
   - Сохраняет пациента в памяти
3. Frontend получает и отображает результаты на StudentViewer/DoctorViewer

---

**Next Step:** Добавьте ваш код расчетов в `app/modules/hip_dysplasia/calculations.py` и готово! ✅
