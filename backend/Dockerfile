FROM python:3.13-slim

# A non-root user to run the app as, instead of the default root.
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy just the dependency list first so Docker can cache this layer and
# skip reinstalling packages when only the app code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
