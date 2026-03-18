# 🏥 MedTech Hip Dysplasia Backend

Professional FastAPI backend for medical image analysis using modular plugin architecture. Designed for hackathon with **extensibility** as core principle.

## 🎯 Architecture: Modular Monolith

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React + Vite)                    │
│           http://localhost:5173 / http://localhost:3000        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────┴──────────────────────────────────────┐
│                    FastAPI Backend                              │
│              http://localhost:8000                              │
├──────────────────────────────────────────────────────────────────┤
│  app/api/                          app/core/                     │
│  ├─ diagnosis_router.py           ├─ config.py (CORS, paths)    │
│  └─ patients_router.py            ├─ lifespan.py (ML loading)   │
│                                     ├─ ml_loader.py (YOLO,      │
│                                     │  MedSAM loader)           │
│                                     └─ patient_store.py (in-mem) │
│                                                                  │
│  app/modules/                                                    │
│  ├─ base.py (BaseDiagnosticModule - abstract class)             │
│  ├─ hip_dysplasia/                                              │
│  │  ├─ module.py (HipDysplasiaModule)                          │
│  │  └─ calculations.py 🔴 YOUR CODE HERE                       │
│  ├─ scoliosis/ (next module - same structure)                   │
│  └─ ...                                                          │
├──────────────────────────────────────────────────────────────────┤
│  ML Models (Lazy-loaded on startup)                             │
│  ├─ YOLO26n-seg (segmentation: femur, ilium, pubis_ischium)    │
│  └─ MedSAM (optional: advanced segmentation)                    │
└──────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
backend/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              ⚙️  Settings (CORS, paths, thresholds)
│   │   ├── lifespan.py            🔄 Startup/shutdown hooks
│   │   ├── ml_loader.py           🤖 Load YOLO + MedSAM
│   │   └── patient_store.py       💾 In-memory patient storage
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── diagnosis_router.py    📤 POST /api/v1/hip-dysplasia/analyze
│   │   └── patients_router.py     📋 Patient management endpoints
│   │
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── base.py                🔴 BaseDiagnosticModule (abstract)
│   │   └── hip_dysplasia/
│   │       ├── __init__.py
│   │       ├── module.py          🦵 Hip dysplasia logic
│   │       └── calculations.py    🔴 YOUR geometric calculations
│   │
│   ├── main.py                    🚀 FastAPI app factory
│   └── __init__.py
│
├── main.py                        🎯 Entry point (uvicorn)
├── requirements.txt               📦 Dependencies
├── .env                           🔐 Configuration
├── .gitignore
├── Dockerfile                     🐳 Container image
├── docker-compose.yml             🐳 Orchestration
├── QUICKSTART.md                  ⚡ Get started in 5 min
├── ARCHITECTURE.md                🏗️  Detailed architecture
└── README.md                      📖 This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Download ML Models

```bash
mkdir -p weights
# Download yolo26n-seg.pt from Ultralytics/Hugging Face
# Place in: weights/yolo26n-seg.pt
```

### 3. Run Backend

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend ready: http://localhost:8000

- Swagger Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

### 4. Integrate Your Calculations

Add your hip dysplasia analysis code to:

```
app/modules/hip_dysplasia/calculations.py
```

See template in that file.

## 📡 API Reference

### Analyze X-ray

```bash
POST /api/v1/hip-dysplasia/analyze
Content-Type: multipart/form-data

Request:
  file: [Binary] DICOM or JPG/PNG image
  patient_name: [Optional] Patient name

Response: 200 OK
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
    "keypoints": {
      "left": [{"name": "femoral_head_center", "x": 100, "y": 200, "confidence": 0.95}],
      "right": [...]
    },
    "masks": {
      "femur": [{"polygon": [[x1,y1], [x2,y2], ...], "confidence": 0.93}],
      "ilium": [...],
      "pubis_ischium": [...]
    },
    "lines": {
      "hilgenreiner_left": {
        "p1": [x1, y1],
        "p2": [x2, y2],
        "equation": "y = 0.05x + 195"
      }
    },
    "measurements_left": {
      "acetabular_angle": 25.5,
      "h_distance": 12.3,
      "d_distance": 8.5
    },
    "measurements_right": {...}
  },
  "metadata": {
    "patient_age": 45,
    "patient_sex": "M",
    "image_size": [512, 512]
  }
}
```

### Patient Management

```bash
GET  /api/v1/patients                       # All patients
GET  /api/v1/patients/{patient_id}         # Patient info
GET  /api/v1/patients/{patient_id}/results # All analyses
GET  /api/v1/patients/{patient_id}/landmarks # Keypoints
```

## 🔌 Extending: Add New Diagnosis Module

### Example: Scoliosis Detection

#### Step 1: Create Module

```bash
mkdir -p app/modules/scoliosis
```

#### Step 2: Implement Module

```python
# app/modules/scoliosis/module.py
from app.modules.base import BaseDiagnosticModule

class ScoliosisModule(BaseDiagnosticModule):
    module_name = "scoliosis"

    async def analyze(self, image_data, patient_age=None, patient_sex=None):
        # Load image
        image_array, metadata = self._load_image(image_data)

        # Your analysis logic
        result = {
            "diagnosis": "normal|scoliosis",
            "confidence": 0.92,
            "cobb_angle": 35.5,
        }

        return {"result": result, "educational_data": {...}}

    def validate_input(self, image_data):
        # Check if image is suitable
        return True
```

#### Step 3: Register in Main App

```python
# app/main.py
from app.modules.scoliosis import ScoliosisModule

scoliosis_router = APIRouter(prefix="/scoliosis", tags=["diagnosis"])

@scoliosis_router.post("/analyze")
async def analyze_scoliosis(file: UploadFile = File(...)):
    analyzer = ScoliosisModule(app.state.models)
    return await analyzer.analyze(await file.read())

app.include_router(scoliosis_router, prefix=settings.API_PREFIX)
```

Done! New endpoint: `POST /api/v1/scoliosis/analyze` 🎉

## 🧠 Where to Add Your Calculations Code

Your geometric calculations should go in:

```
app/modules/hip_dysplasia/calculations.py
```

### Expected Function

```python
def compute_measurements(image_array, segmentation_results):
    """
    Returns: (measurements, keypoints)
    """
    # Calculate Hilgenreiner line
    # Calculate acetabular angle
    # Calculate distances h and d
    # Extract keypoints: femoral head center, acetabular rim, etc.
    # Determine left vs right hip
    return measurements, keypoints
```

### Using in Module

```python
# In app/modules/hip_dysplasia/module.py
from app.modules.hip_dysplasia.calculations import compute_measurements

# In analyze() method:
measurements, keypoints = compute_measurements(image_array, segmentation_results)
```

## 🐳 Docker Deployment

### Build & Run

```bash
cd backend
docker-compose up --build
```

Backend will be at: http://localhost:8000

### With GPU Support

Update `.env`:

```
DEVICE=cuda:0
```

## 🔧 Configuration

### `.env` File

```
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
YOLO_CONF_THRESHOLD=0.5
YOLO_IOU_THRESHOLD=0.45
DEVICE=cpu              # or cuda:0
YOLO_MODEL_PATH=weights/yolo26n-seg.pt
MEDSAM_MODEL_PATH=weights/medsam.pth
```

### Supported Image Formats

- ✅ DICOM (.dcm, .dicom)
- ✅ JPEG (.jpg, .jpeg)
- ✅ PNG (.png)

## 📊 Data Flow

```
1. User uploads X-ray (DICOM/JPG/PNG)
                ↓
2. DICOM → Extract age metadata (pydicom)
   JPG/PNG → Load with PIL
                ↓
3. YOLO Segmentation
   Output: Masks for [femur, ilium, pubis_ischium]
                ↓
4. compute_measurements() 🔴 YOUR CODE
   Input: image, masks
   Output: keypoints, angles, distances, lines
                ↓
5. Format response with educational data
                ↓
6. Store patient results in-memory
                ↓
7. Return JSON with diagnosis + detailed analysis
```

## 🧪 Testing

### Manual Test with Swagger

```
http://localhost:8000/docs
```

Click on `/api/v1/hip-dysplasia/analyze` → Try it out → Upload file

### Test with curl

```bash
curl -X POST \
  -F "file=@path/to/image.jpg" \
  http://localhost:8000/api/v1/hip-dysplasia/analyze
```

## 📈 Performance

- **Model Loading:** ~2-3 seconds (done once at startup)
- **Per-Request Analysis:** ~0.5-1.5 seconds (image load + YOLO inference)
- **Memory:** ~2-3 GB (YOLO + CUDA)

## ⚠️ Important Notes

1. **ML Models are NOT included** - Download separately
2. **Patient data is in-memory** - Restart app clears data (use DB for production)
3. **Single GPU box** - Consider load balancing for production
4. **CORS is open to localhost** - Restrict in production

## 🚧 Production Checklist

- [ ] Add database (PostgreSQL, MongoDB)
- [ ] Implement authentication (JWT)
- [ ] Add rate limiting
- [ ] Enable HTTPS
- [ ] Use secrets manager for API keys
- [ ] Add request logging
- [ ] Setup monitoring (Prometheus, Grafana)
- [ ] Load test
- [ ] Security audit

## 📞 Support

See also:

- [QUICKSTART.md](QUICKSTART.md) - 5-minute setup
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed design
- Frontend integration guide in [../INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md)

---

**Built with ❤️ for medical AI diagnostics**
