# syntax=docker/dockerfile:1

FROM python:latest AS deps

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

WORKDIR /app

RUN python -m pip install poetry

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi

FROM python:latest

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=deps /app/.venv /app/.venv
COPY main.py env.py scheduler.py ./

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/.data/session /app/.data/logs \
    && chown -R appuser:appuser /app

USER appuser

VOLUME ["/app/.data"]

CMD ["python", "scheduler.py"]
