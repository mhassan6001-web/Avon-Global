# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN groupadd --system aven && useradd --system --gid aven --home /app aven

FROM base AS dev
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt
COPY . .
USER aven
EXPOSE 8000
CMD ["sh", "scripts/start-dev.sh"]

FROM base AS production
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY --chown=aven:aven app ./app
COPY --chown=aven:aven alembic ./alembic
COPY --chown=aven:aven alembic.ini ./
USER aven
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=2).status == 200 else 1)"
# Migrations run as a separate release step in production (see README), never on every start.
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--no-server-header"]
