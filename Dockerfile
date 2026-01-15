# syntax=docker/dockerfile:1

FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app/backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist ./static
EXPOSE 8000
CMD ["uvicorn", "app:asgi_app", "--host", "0.0.0.0", "--port", "8000"]
