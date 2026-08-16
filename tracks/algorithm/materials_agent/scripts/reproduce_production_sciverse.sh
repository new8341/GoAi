#!/usr/bin/env bash
# Official reproduce path for production_sciverse.
# Does NOT call scripts/maintenance/* repair scripts.
# Requires: SCIVERSE_API_TOKEN, local GROBID.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== healthcheck =="
python scripts/healthcheck.py -c configs/production_sciverse.yaml || {
  echo "healthcheck RED. Start GROBID or set SCIVERSE_API_TOKEN, then retry."
  exit 1
}

echo "== survey =="
python scripts/run_survey.py survey -c configs/production_sciverse.yaml

echo "== verify =="
python scripts/verify_production.py -c configs/production_sciverse.yaml

echo "== science =="
python scripts/science_review_gate.py -c configs/production_sciverse.yaml --run outputs/production_sciverse

echo "== objective =="
python scripts/objective_review_run.py --run outputs/production_sciverse

echo "reproduce done. Check production_verification.json + science_review.json + objective_review.json"
