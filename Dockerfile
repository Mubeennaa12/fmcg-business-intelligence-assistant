# Stage 1: Build Next.js Static Pages
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend-build

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Serve full-stack application via FastAPI
FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy static frontend HTML/JS/CSS assets into FastAPI static files directory
COPY --from=frontend-builder /frontend-build/out/ ./static/

# Hugging Face Spaces port defaults to 7860
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
