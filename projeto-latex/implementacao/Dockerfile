FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY tests ./tests
COPY pytest.ini ./pytest.ini
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
