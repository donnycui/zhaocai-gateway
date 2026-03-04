FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway.py .
COPY providers ./providers
COPY control_plane ./control_plane
COPY scripts ./scripts
COPY config.example.yaml ./config.yaml

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["python", "gateway.py"]

