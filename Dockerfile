# ActTrace API — glibc Python base (bcrypt/pydantic wheels are glibc).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY backend/ ./backend/

ENV ACTTRACE_DB_PATH=/data/acttrace.sqlite3 \
    ACTTRACE_API_KEY_AUTH=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8080"]
