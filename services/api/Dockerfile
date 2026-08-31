# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/agas-venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /build

RUN python -m venv "${VIRTUAL_ENV}"

COPY pyproject.toml README.md ./
COPY data ./data
COPY packages ./packages
COPY services ./services

RUN python -m pip install --upgrade pip && \
    python -m pip install .


FROM python:3.12-slim AS runtime

ENV PATH="/opt/agas-venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10001 agas && \
    useradd --uid 10001 --gid agas --no-log-init --create-home agas

WORKDIR /app

COPY --from=builder /opt/agas-venv /opt/agas-venv
COPY alembic.ini ./alembic.ini
COPY migrations ./migrations

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"]

CMD ["uvicorn", "agas_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
