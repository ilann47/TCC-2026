FROM node:24.16.0-bookworm-slim@sha256:2c87ef9bd3c6a3bd4b472b4bec2ce9d16354b0c574f736c476489d09f560a203 AS frontend
WORKDIR /frontend
COPY demo/resultados-ui/package*.json ./
RUN npm ci --no-audit --no-fund
COPY demo/resultados-ui/ ./
RUN npm run build

FROM python:3.13-alpine@sha256:7415fbc3c9e4979cc717d92377ab2bc7b2b4a2af1ac03cc52b5f3f88efedaf3a
RUN apk add --no-cache bash curl util-linux docker-cli docker-cli-compose
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/implementacao-java
COPY --from=frontend /frontend/dist /opt/tcc-results
COPY demo/container_runtime.py /opt/tcc/container_runtime.py
ENTRYPOINT ["python3", "-B", "/opt/tcc/container_runtime.py"]
