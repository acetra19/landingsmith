FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p data output

ENV PORT=8000

EXPOSE ${PORT}

CMD uvicorn dashboard.app:app --host 0.0.0.0 --port ${PORT}
