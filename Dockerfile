ARG PYTHON_IMAGE=python:3.12-alpine@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Apply available distribution security fixes before installing application deps.
RUN apk upgrade --no-cache

COPY api/requirements.lock ./requirements.lock
RUN python -m pip install --no-cache-dir --only-binary=:all: -r requirements.lock

RUN addgroup -g 10001 api \
    && adduser -D -H -u 10001 -G api -s /sbin/nologin api

COPY --chown=10001:10001 api/ ./

USER 10001:10001
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
