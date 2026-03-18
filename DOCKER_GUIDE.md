# Docker Compose Setup Guide

## Overview

This guide covers running both the backend and frontend services using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- YOLO model file (`yolov8n-seg.pt`) for the backend

## Quick Start

### Option 1: Run from root directory (Recommended)

```bash
docker-compose up
```

This will:

- Build and start the backend on `http://localhost:8000`
- Build and start the frontend on `http://localhost:3000`
- Create a shared network for inter-service communication

### Option 2: Run from backend directory

```bash
cd backend
docker-compose up
```

## Configuration

### Backend

**Environment Variables:**

- `DEVICE`: CPU/GPU device ('cpu' by default)
- `CORS_ORIGINS`: Allowed origins for CORS (defaults include localhost and frontend container)

**Volumes:**

- `./backend/weights:/app/weights` - YOLO model storage
- `./backend/app:/app/app` - Live code updates during development

**Port:** 8000

### Frontend

**Environment Variables:**

- `VITE_API_URL`: Backend API URL (defaults to `http://backend:8000` for Docker)

**Port:** 3000

## Setup Steps

### 1. Download YOLO Model

Before running Docker Compose, download the YOLO model:

```bash
cd backend/weights
# Use your preferred method to download yolov8n-seg.pt
# Or the model will auto-download on first run if configured
```

### 2. Build Images

```bash
docker-compose build
```

### 3. Start Services

```bash
# Start in foreground (logs visible)
docker-compose up

# Or start in background
docker-compose up -d
```

### 4. Check Health

```bash
# Backend health check
curl http://localhost:8000/api/v1/health

# Frontend
curl http://localhost:3000
```

## Common Commands

```bash
# Stop services
docker-compose stop

# Stop and remove containers
docker-compose down

# View logs
docker-compose logs

# View specific service logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild images
docker-compose build --no-cache

# Run command in container
docker-compose exec backend python -c "import torch; print(torch.__version__)"
```

## Network Communication

- **Frontend to Backend:** `http://backend:8000` (internal Docker network)
- **External Access:**
  - Backend: `http://localhost:8000`
  - Frontend: `http://localhost:3000`

## Troubleshooting

### Backend won't start

- Check logs: `docker-compose logs backend`
- Verify YOLO model exists in `backend/weights/`
- Ensure port 8000 is not occupied

### Frontend can't reach backend

- Verify backend is running: `docker-compose ps`
- Check backend is healthy: `docker-compose logs backend`
- Ensure both services are on the same network

### CORS errors

- Backend CORS_ORIGINS should include frontend URL
- Check docker-compose.yml CORS_ORIGINS setting

## Development Workflow

### Backend Changes

```bash
# Code changes are reflected automatically (volume mounted)
# Restart if needed
docker-compose restart backend
```

### Frontend Changes

```bash
# Rebuild and restart
docker-compose restart frontend
```

## Production Deployment

For production deployment:

1. Remove volume mounts (in frontend section)
2. Set `DEVICE=cuda` if GPU available
3. Use environment-specific docker-compose files
4. Add SSL/TLS configuration
5. Configure proper CORS origins

## Structure

```
neurovzor/
├── docker-compose.yml (root level)
├── backend/
│   ├── Dockerfile
│   ├── docker-compose.yml (alternative)
│   ├── requirements.txt
│   ├── app/
│   └── weights/
└── frontend/
    ├── Dockerfile
    ├── package.json
    └── src/
```

## Notes

- Frontend is built using multi-stage build for smaller image size
- Backend uses Python 3.11 slim image for efficiency
- Both services communicate via internal Docker network
- Health checks configured for backend
- Frontend depends_on backend to ensure startup order
