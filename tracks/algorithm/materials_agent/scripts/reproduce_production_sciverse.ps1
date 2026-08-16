# Official reproduce path for production_sciverse.
# Does NOT call scripts/maintenance/* repair scripts.
# Requires: SCIVERSE_API_TOKEN, local GROBID (docker compose up -d grobid).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "== healthcheck =="
py scripts/healthcheck.py -c configs/production_sciverse.yaml
if ($LASTEXITCODE -eq 1) {
  Write-Host "healthcheck RED. Start GROBID or set SCIVERSE_API_TOKEN, then retry."
  exit 1
}

Write-Host "== survey =="
py scripts/run_survey.py survey -c configs/production_sciverse.yaml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== verify =="
py scripts/verify_production.py -c configs/production_sciverse.yaml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== science =="
py scripts/science_review_gate.py -c configs/production_sciverse.yaml --run outputs/production_sciverse
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== objective =="
py scripts/objective_review_run.py --run outputs/production_sciverse
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "reproduce done. Check production_verification.json + science_review.json + objective_review.json"
