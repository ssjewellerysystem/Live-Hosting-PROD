FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY backend/requirements.txt ./backend/requirements.txt

RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY backend ./backend
COPY migrations ./migrations

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --home-dir /home/app app \
    && mkdir -p /app/backend/static/uploads /app/backend/reports \
    && chown -R app:app /app /home/app

USER app

EXPOSE 5005

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5005/health', timeout=3).read()"]

CMD ["gunicorn", "--bind", "0.0.0.0:5005", "--workers", "2", "--threads", "2", "--worker-class", "gthread", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "backend.app:app"]
