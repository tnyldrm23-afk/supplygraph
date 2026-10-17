FROM python:3.12.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements-lock.txt && useradd --uid 10001 --create-home app
COPY --chown=app:app LICENSE DATA_LICENSE.md ./
COPY --chown=app:app app ./app
COPY --chown=app:app data/processed ./data/processed
USER app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=10s --start-period=90s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
