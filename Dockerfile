# 1단계: Vite 프론트엔드 빌드
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2단계: Python 백엔드 + 정적 프론트엔드 서빙
FROM python:3.11-slim
WORKDIR /app

# Python 의존성
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 백엔드 코드
COPY backend/ ./

# 1단계에서 빌드된 frontend/dist → /app/static
COPY --from=frontend-builder /app/frontend/dist ./static

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
