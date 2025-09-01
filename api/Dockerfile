FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mepquiz /app/mepquiz

# Include Alembic config & migration scripts in the image
COPY alembic.ini /app/alembic.ini
COPY alembic /app/alembic

EXPOSE 8000

# Default command (API). The worker service will override this in docker-compose.
CMD ["uvicorn", "mepquiz.main:app", "--host", "0.0.0.0", "--port", "8000"]
