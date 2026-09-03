# Single image for both docker-compose services (dagster, dashboard):
# simpler to build and maintain than two images, at the cost of the
# dashboard container carrying dependencies (dagster, dbt) it doesn't use
# at runtime — a fine trade-off for a local/demo deployment.
FROM python:3.11-slim

WORKDIR /app

# System deps: git is needed by some dbt/dagster tooling at install time.
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml requirements.txt ./
COPY src ./src
COPY README.md ./

RUN pip install --no-cache-dir -e ".[dev,orchestration]" \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DAGSTER_HOME=/app/orchestration
