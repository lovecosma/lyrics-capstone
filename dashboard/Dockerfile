FROM python:3.14-slim

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

# One worker because every worker loads all the dashboard data into memory;
# --preload loads it once before gunicorn starts serving
CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --preload app:server
