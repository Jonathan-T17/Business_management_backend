FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.txt
COPY deployment/requirements-production.txt requirements-production.txt
RUN pip install --no-cache-dir -r requirements.txt -r requirements-production.txt
COPY . .
RUN DJANGO_SETTINGS_MODULE=Business_management_backend.settings_build SECRET_KEY=build-only-placeholder DB_NAME=build DB_USER=build DB_PASSWORD=build DB_HOST=localhost DB_PORT=5432 python manage.py collectstatic --noinput
CMD ["gunicorn", "Business_management_backend.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
