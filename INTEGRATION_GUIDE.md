# 🚀 РУКОВОДСТВО ПО ЗАПУСКУ ИНТЕГРИРОВАННОЙ СИСТЕМЫ

## Структура проекта

```
Frontend (React + Vite) --HTTP--> Backend (FastAPI) ---> ML Models
         :3000/5173                    :8000
```

## Быстрый старт

### 1️⃣ Подготовка Backend

```bash
# Перейти в папку backend
cd backend

# Установить зависимости
pip install -r requirements.txt

# (Опционально) Скачать ML-модели в папку weights/
# mkdir -p weights
# Download weights here

# Запустить FastAPI сервер (dev режим)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API доступен на: **http://localhost:8000**
- Health check: `/api/v1/health`
- Swagger docs: `/docs`

### 2️⃣ Подготовка Frontend

```bash
# Перейти в папку frontend
cd frontend

# Установить зависимости
npm install

# Запустить Vite dev server
npm run dev
```

Приложение доступно на: **http://localhost:5173** или **http://localhost:3000**

### 3️⃣ Запуск через Docker Compose (оборо производства)

```bash
cd backend

# Собрать и запустить оба сервиса
docker-compose up --build

# Backend будет на http://localhost:8000
# Frontend нужно запустить отдельно: npm run dev
```

---

## 📡 API Integration Guide

### Основной эндпоинт анализа

```bash
POST /api/v1/hip-dysplasia/analyze
Content-Type: multipart/form-data

Parameters:
  - file: [Binary] DICOM, JPG или PNG рентгенограмма
  - patient_name: [Optional] Имя пациента

Response:
{
  "patient_id": "ПТ-2024-0001",
  "module": "hip_dysplasia",
  "status": "success",
  "result": {
    "diagnosis": "normal|dysplasia|subluxation|dislocation",
    "confidence": 0.95,
    "side_affected": "none|left|right|bilateral",
    "putti_triad": {...}
  },
  "educational_data": {
    "xray_quality": {...},
    "masks": {...},
    "keypoints": {...},
    "lines": {...},
    "measurements_left": {...},
    "measurements_right": {...}
  }
}
```

### Получение результатов пациента

```bash
# Список всех пациентов
GET /api/v1/patients

# Информация о пациенте
GET /api/v1/patients/{patient_id}

# Ориентиры для визуализации
GET /api/v1/patients/{patient_id}/landmarks

# Результаты анализа
GET /api/v1/patients/{patient_id}/results

# Уверенность диагноза
GET /api/v1/patients/{patient_id}/confidence
```

---

## 🔧 Configuration

### Backend (.env)
```
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
YOLO_CONF_THRESHOLD=0.5
DEVICE=cpu  # или cuda:0 для GPU
```

### Frontend (.env.local)
```
VITE_API_BASE=/api/v1
```

---

## 🐛 Troubleshooting

### CORS Errors
- ✅ Убедитесь, что Backend CORS настроен для http://localhost:3000 и http://localhost:5173
- Проверьте `/backend/app/core/config.py` -> `CORS_ORIGINS`

### API Connection Failed
- ✅ Проверьте, что Backend запущен на `http://localhost:8000`
- Проверьте Vite прокси в `/frontend/vite.config.js`
- Используйте `npm run dev` для запуска фронтенда

### Файл загружается, но ошибка 422
- ✅ Формат файла должен быть: DICOM, JPG или PNG
- Проверьте размер файла
- Посмотрите ошибку в консоли Backend

### ML-модели не найдены
- ✅ Создайте папку `backend/weights/`
- Скачайте модели и положите в эту папку
- Переименуйте в `yolo_hip.pt` и `medsam.pth`

---

## 📊 Workflow

1. **Пользователь загружает рентгенограмму** на главной странице (UploadPage)
2. **Frontend** отправляет файл на `/api/v1/hip-dysplasia/analyze`
3. **Backend** обрабатывает файл:
   - Ищет хрящи, кости (YOLO)
   - Сегментирует структуры (MedSAM)
   - Вычисляет геометрию и углы
   - Сохраняет пациента в памяти
4. **Frontend** получает результаты с `patient_id`
5. **Пациент** переходит на страницу просмотра (StudentViewer/DoctorViewer)
6. **Фронтенд** загружает ориентиры и результаты через другие эндпоинты

---

## 📝 Files Modified/Created

### Backend
- ✅ `app/core/patient_store.py` - In-memory хранилище пациентов
- ✅ `app/api/patients_router.py` - Роутер для управления пациентами
- ✅ `app/api/router.py` - Подключение нового роутера
- ✅ `app/modules/hip_dysplasia/router.py` - Обновлен для сохранения результатов
- ✅ `app/core/config.py` - Обновлена CORS конфигурация

### Frontend
- ✅ `src/services/api.js` - API-сервис для запросов
- ✅ `src/components/ui/FileUploader/FileUploader.jsx` - Обновлен для загрузки файлов
- ✅ `src/pages/UploadPage/UploadPage.jsx` - Интеграция с API
- ✅ `src/pages/StudentViewer/StudentViewer.jsx` - Интеграция с API
- ✅ `src/pages/DoctorViewer/DoctorViewer.jsx` - Переписан для работы с API
- ✅ `vite.config.js` - Прокси и конфигурация API_BASE

### Configuration
- ✅ `frontend/.env.local` - Переменные окружения фронтенда
- ✅ `backend/.env` - Переменные окружения бэкенда

---

## ✅ Checklist перед продакшном

- [ ] Скачаны ML-модели (YOLO + MedSAM)
- [ ] Настроены пути к весам в `backend/.env`
- [ ] Тестирование CORS на целевых доменах
- [ ] Безопасность: установлены конкретные CORS origins (не "*")
- [ ] БД для персистентного хранилища пациентов (сейчас in-memory)
- [ ] Аутентификация и авторизация (если требуется)
- [ ] Логирование и мониторинг на продакшене
- [ ] SSL/TLS сертификаты для HTTPS

---

## 🎯 Next Steps

1. **Полнофункциональное хранилище**: Заменить in-memory store на PostgreSQL/MongoDB
2. **Аутентификация**: Добавить JWT или OAuth для врачей
3. **История версий**: Добавить версионирование анализов
4. **Экспорт отчетов**: PDF/DICOM экспорт результатов
5. **Масштабирование**: Celery для асинхронной обработки анализов

---

**Вопросы? Проверьте консоль браузера (DevTools) и логи Backend!**
