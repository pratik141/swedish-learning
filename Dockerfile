FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "python -m scripts.migrate_database && exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --access-logfile - --error-logfile - server:app"]
