FROM node:20-alpine AS web-build

WORKDIR /web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY zhaocai_gateway ./zhaocai_gateway
COPY agent ./agent
COPY README.md .
COPY .env.example .
COPY config.example.yaml .
COPY --from=web-build /web/dist ./web-dist

ENV ZHAOCAI_WEB_DIST=/app/web-dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health').raise_for_status()"

CMD ["python", "-m", "zhaocai_gateway.main"]
