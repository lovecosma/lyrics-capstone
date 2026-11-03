FROM python:3.14.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8050

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home dash
USER dash

EXPOSE ${PORT}

# One worker, because each worker would hold its own copy of the data in memory.
# --preload loads the data before gunicorn opens the port, so Cloud Run's startup probe waits for it
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --preload app:server
