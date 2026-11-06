FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/zenith/.cache/huggingface

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /usr/sbin/nologin zenith \
    && mkdir -p /app/uploaded_documents /data /home/zenith/.cache/huggingface \
    && chown -R zenith:zenith /app /data /home/zenith/.cache

COPY --chown=zenith:zenith . .
RUN chmod 755 /app/docker-entrypoint.sh

USER zenith
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
