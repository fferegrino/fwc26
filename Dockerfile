FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Install dependencies first (better Docker layer caching)
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi

# Copy the rest of the app (frontend assets + main.py)
COPY . .

EXPOSE 8080

CMD ["sh", "-c", "poetry run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
