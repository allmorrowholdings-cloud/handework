FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home handework && chown -R handework:handework /app
USER handework
CMD ["sh", "-c", "gunicorn --worker-class gthread --threads 4 --workers 2 --bind 0.0.0.0:${PORT:-5000} wsgi:app"]
