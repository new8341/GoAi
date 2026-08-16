# Reproducible stack for materials_agent (GROBID + Qdrant + app shell)
#
# Usage:
#   docker compose up -d grobid qdrant
#   docker build -t materials-agent:local -f Dockerfile .
#   docker run --rm -it --env-file .env -v "%CD%/outputs:/app/outputs" materials-agent:local \
#     py -3 scripts/run_survey.py survey -c configs/demo_local.yaml
#
# Full production hybrid (Sciverse+Sci-Base) still needs host network access to
# localhost:8070 GROBID or compose network aliases.

FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml README.md ./
COPY materials_agent ./materials_agent
COPY scripts ./scripts
COPY configs ./configs
COPY experiments ./experiments
COPY docs ./docs
COPY DEPENDENCIES.md 使用说明.md ./

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e ".[scibase]" || pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "scripts/run_survey.py", "survey", "-c", "configs/demo_local.yaml"]
