# Stage 1: Build React Dashboard
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python Backend & Static Server
FROM python:3.10-slim
WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends curl zip && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend code, plugin, and built frontend
COPY backend/ ./backend/
COPY wp-plugin/ ./wp-plugin/
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Ensure plugin zips are fresh
RUN cd wp-plugin && zip -FSr ai-news-publisher.zip ai-news-publisher/ && cp ai-news-publisher.zip pulse-content-sync.zip || true
RUN cp wp-plugin/pulse-content-sync.zip frontend/dist/pulse-content-sync.zip || true

EXPOSE 8081
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0

CMD ["sh", "-c", "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8081}"]
