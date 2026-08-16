# Build GOAI Track-3 materials_agent submission zips (Windows PowerShell)
# Official portal name (document/xiuding.md): AI4R_ALG_MAT_和昆仑.zip
# Usage:
#   .\build_submission_packages.ps1
#   .\build_submission_packages.ps1 -SemiFinal
param(
  [switch]$SemiFinal
)
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Submissions = Resolve-Path (Join-Path $ScriptDir "..")
$RepoRoot = Resolve-Path (Join-Path $Submissions "..")
$Agent = Join-Path $RepoRoot "tracks\algorithm\materials_agent"
$OutDir = Join-Path $Submissions "packages"
$Stamp = Get-Date -Format "yyyyMMdd_HHmm"
# Team name 和昆仑 via codepoints so script encoding cannot corrupt the portal filename.
$TeamName = -join @([char]0x548C, [char]0x6606, [char]0x4ED1)
$OfficialName = "AI4R_ALG_MAT_${TeamName}.zip"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Add-Type -AssemblyName System.IO.Compression.FileSystem
function New-ZipFromDir($SourceDir, $ZipPath) {
  # Write to ASCII temp zip then File.Move to final name (avoids Unicode path bugs).
  $dir = Split-Path -Parent $ZipPath
  $leaf = Split-Path -Leaf $ZipPath
  $needsRename = $leaf -match "[^\x00-\x7F]"
  $tmpZip = if ($needsRename) {
    Join-Path $dir ("_tmp_" + [Guid]::NewGuid().ToString("N") + ".zip")
  } else {
    $ZipPath
  }
  if (Test-Path -LiteralPath $ZipPath) { Remove-Item -LiteralPath $ZipPath -Force }
  if (Test-Path -LiteralPath $tmpZip) { Remove-Item -LiteralPath $tmpZip -Force }
  [System.IO.Compression.ZipFile]::CreateFromDirectory(
    (Resolve-Path $SourceDir).Path,
    $tmpZip,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
  )
  if ($needsRename) {
    if ([System.IO.File]::Exists($ZipPath)) { [System.IO.File]::Delete($ZipPath) }
    [System.IO.File]::Move($tmpZip, $ZipPath)
  }
}

# ---- 1) Preliminary docs ----
$DocsStage = Join-Path $OutDir "_stage_docs_$Stamp"
New-Item -ItemType Directory -Force -Path $DocsStage | Out-Null
Copy-Item (Join-Path $Submissions "preliminary\*.md") $DocsStage
$DocsZip = Join-Path $OutDir "GOAI_T3_materials_preliminary_docs_$Stamp.zip"
New-ZipFromDir $DocsStage $DocsZip
Remove-Item $DocsStage -Recurse -Force
Write-Host "docs=$DocsZip"

# ---- 2) Evidence snapshot ----
$EvStage = Join-Path $OutDir "_stage_evidence_$Stamp"
$EvSci = Join-Path $EvStage "production_sciverse"
$EvRa = Join-Path $EvStage "production_route_a"
New-Item -ItemType Directory -Force -Path $EvSci, $EvRa | Out-Null
$sciFiles = @(
  "production_verification.json", "science_review.json", "objective_review.json",
  "optimization_metrics.json", "gaps.json", "papers.json", "report.md",
  "report.tex", "references.bib", "report.pdf", "external_versions.json",
  "consistency.json", "audit.json", "fulltext_index.json",
  "route_a_run_summary.json", "route_a_external_validation.json",
  "route_a_spr_report.md", "route_a_spr_candidates.json"
)
$missingLatex = @()
foreach ($f in @("report.tex", "references.bib", "report.pdf")) {
  $p = Join-Path $Agent "outputs\production_sciverse\$f"
  if (-not (Test-Path $p)) { $missingLatex += $f }
}
if ($missingLatex.Count -gt 0) {
  Write-Warning ("Missing survey artifacts in production_sciverse: {0}. Run: py -3 scripts/export_survey_latex.py outputs/production_sciverse" -f ($missingLatex -join ", "))
}
foreach ($f in $sciFiles) {
  $p = Join-Path $Agent "outputs\production_sciverse\$f"
  if (Test-Path $p) { Copy-Item $p $EvSci }
}
$raFiles = @(
  "route_a_run_summary.json", "route_a_external_validation.json",
  "route_a_spr_report.md", "route_a_spr_candidates.json"
)
foreach ($f in $raFiles) {
  $p = Join-Path $Agent "outputs\production_route_a\$f"
  if (Test-Path $p) { Copy-Item $p $EvRa }
}
$def = Join-Path $Agent "outputs\defense_pack.json"
if (Test-Path $def) { Copy-Item $def $EvStage }
$rev = Join-Path $Agent "experiments\reviews"
$revOut = Join-Path $EvStage "reviews"
New-Item -ItemType Directory -Force -Path $revOut | Out-Null
@(
  "defense_pack.md",
  "expert-6rounds-20260811-production_sciverse.md",
  "architecture-expert-audit-20260811.md",
  "science-review-2026-08-11-production_sciverse.md",
  "review-20260811-objective-production_sciverse.md",
  "README.md"
) | ForEach-Object {
  $p = Join-Path $rev $_
  if (Test-Path $p) { Copy-Item $p $revOut }
}
$EvZip = Join-Path $OutDir "GOAI_T3_materials_evidence_$Stamp.zip"
New-ZipFromDir $EvStage $EvZip
Write-Host "evidence=$EvZip"

# ---- 3) Code package (desensitized) ----
$CodeStageRoot = Join-Path $OutDir "_stage_code_$Stamp"
$CodeStage = Join-Path $CodeStageRoot "materials_agent"
New-Item -ItemType Directory -Force -Path $CodeStage | Out-Null
$include = @(
  "materials_agent", "scripts", "configs", "tests", "user", "viewer",
  "experiments", "docs",
  "README.md", "使用说明.md", "完成度与优化方向.md", "DEPENDENCIES.md",
  "readme_agent.md", "requirements.txt", "docker-compose.yml", ".env.example"
)
foreach ($name in $include) {
  $src = Join-Path $Agent $name
  if (Test-Path $src) {
    $dst = Join-Path $CodeStage $name
    if (Test-Path $src -PathType Container) {
      robocopy $src $dst /E /XD __pycache__ .pytest_cache .git data models `
        /XF *.pyc .env *.pdf *.baiduyun.uploading.cfg /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
      if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $name code=$LASTEXITCODE" }
    } else {
      Copy-Item $src $dst
    }
  }
}
$OutMini = Join-Path $CodeStage "outputs\_submission_pointers"
New-Item -ItemType Directory -Force -Path $OutMini | Out-Null
@"
# Submission pointers (full gold runs are in the evidence folder of the portal zip)

- Gold literature: production_sciverse (LLM-off)
- Route A: production_route_a
- Official portal zip name: AI4R_ALG_MAT_和昆仑.zip (see document/xiuding.md)
- Do not commit .env or paywalled PDFs
"@ | Set-Content -Encoding UTF8 (Join-Path $OutMini "README.md")

$CompDst = Join-Path $CodeStage "compliance"
New-Item -ItemType Directory -Force -Path $CompDst | Out-Null
if (Test-Path (Join-Path $RepoRoot "compliance")) {
  Copy-Item (Join-Path $RepoRoot "compliance\*") $CompDst -Recurse -Force
}

$CodeZip = Join-Path $OutDir "GOAI_T3_materials_code_$Stamp.zip"
if (Test-Path $CodeZip) { Remove-Item $CodeZip -Force }
New-ZipFromDir $CodeStage $CodeZip
Write-Host "code=$CodeZip"

# ---- 4) Official portal zip: AI4R_ALG_MAT_和昆仑.zip ----
$PortalStage = Join-Path $OutDir "_stage_portal_$Stamp"
New-Item -ItemType Directory -Force -Path $PortalStage | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "01_docs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "02_code") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "03_survey_report") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "04_evidence") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "05_compliance") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "06_route_a") | Out-Null

if ($SemiFinal) {
  Copy-Item (Join-Path $Submissions "semi_final\*.md") (Join-Path $PortalStage "01_docs") -Force
  Copy-Item (Join-Path $Submissions "preliminary\01_*.md") (Join-Path $PortalStage "01_docs") -Force -ErrorAction SilentlyContinue
  Copy-Item (Join-Path $Submissions "preliminary\02_*.md") (Join-Path $PortalStage "01_docs") -Force -ErrorAction SilentlyContinue
  Copy-Item (Join-Path $Submissions "preliminary\04_*.md") (Join-Path $PortalStage "01_docs") -Force -ErrorAction SilentlyContinue
  # 0816: also place Route A explanation next to SPR artifacts
  $raExplain = Join-Path $Submissions "semi_final\route_a_explanation.md"
  if (Test-Path $raExplain) { Copy-Item $raExplain (Join-Path $PortalStage "06_route_a") -Force }
  $sysDesc = Join-Path $Submissions "semi_final\system_description.md"
  if (Test-Path $sysDesc) { Copy-Item $sysDesc (Join-Path $PortalStage "03_survey_report") -Force }
} else {
  Copy-Item (Join-Path $Submissions "preliminary\*.md") (Join-Path $PortalStage "01_docs")
}
robocopy $CodeStage (Join-Path $PortalStage "02_code\materials_agent") /E `
  /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy portal code failed code=$LASTEXITCODE" }

$reportSrc = Join-Path $Agent "outputs\production_sciverse_scibase"
if (-not (Test-Path (Join-Path $reportSrc "report.pdf"))) {
  $reportSrc = Join-Path $Agent "outputs\production_sciverse"
}
foreach ($f in @("report.pdf", "report.tex", "references.bib", "report.md", "external_versions.json")) {
  $p = Join-Path $reportSrc $f
  if (Test-Path $p) { Copy-Item $p (Join-Path $PortalStage "03_survey_report") }
}

# slim evidence (JSON/MD only already staged)
robocopy $EvStage (Join-Path $PortalStage "04_evidence") /E `
  /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy portal evidence failed code=$LASTEXITCODE" }

if ($SemiFinal) {
  $sb = Join-Path $Agent "experiments\scibase\materials_cache.jsonl"
  if (Test-Path $sb) {
    New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "04_evidence\scibase") | Out-Null
    Copy-Item $sb (Join-Path $PortalStage "04_evidence\scibase\materials_cache.jsonl") -Force
    $sbMd = Join-Path $Submissions "semi_final\scibase_usage.md"
    if (Test-Path $sbMd) { Copy-Item $sbMd (Join-Path $PortalStage "04_evidence\scibase") -Force }
  }
  $enrich = Join-Path $Agent "outputs\production_sciverse_scibase\scibase_enrichment.json"
  if (Test-Path $enrich) {
    New-Item -ItemType Directory -Force -Path (Join-Path $PortalStage "04_evidence\scibase") | Out-Null
    Copy-Item $enrich (Join-Path $PortalStage "04_evidence\scibase") -Force
  }
  $dual = Join-Path $Agent "outputs\production_route_a\route_a_external_validation_mp_oqmd.json"
  if (Test-Path $dual) { Copy-Item $dual (Join-Path $PortalStage "06_route_a") -Force }
}

if (Test-Path (Join-Path $RepoRoot "compliance")) {
  Copy-Item (Join-Path $RepoRoot "compliance\*") (Join-Path $PortalStage "05_compliance") -Recurse -Force
}
# Route A + ablation + stability (semi-final)
$raSrc = Join-Path $Agent "outputs\production_route_a"
$abSrc = Join-Path $Agent "outputs\ablation_route_a"
foreach ($f in @("route_a_spr_report.md","route_a_run_summary.json","route_a_external_validation.json","route_a_spr_candidates.json")) {
  $p = Join-Path $raSrc $f
  if (Test-Path $p) { Copy-Item $p (Join-Path $PortalStage "06_route_a") }
}
if (Test-Path $abSrc) {
  foreach ($f in @("ablation_compare.json")) {
    $p = Join-Path $abSrc $f
    if (Test-Path $p) { Copy-Item $p (Join-Path $PortalStage "06_route_a") }
  }
}
$stab = Join-Path $Agent "outputs\stability_demo\stability_summary.json"
if (Test-Path $stab) { Copy-Item $stab (Join-Path $PortalStage "06_route_a") }

$stageLabel = if ($SemiFinal) { "复赛" } else { "初赛" }
@"
# AI4R_ALG_MAT_和昆仑 — ${stageLabel}提交包

命名依据：document/xiuding.md「提交物命名规范」
格式：赛道_类型_方向_队伍名.zip → AI4R_ALG_MAT_和昆仑.zip
SemiFinal=$SemiFinal

## 目录

| 目录 | 内容 |
|------|------|
| 01_docs | 方案/复赛清单/系统说明/科学意义/消融/复现说明 |
| 02_code | 脱敏源代码（含 configs 种子与参数） |
| 03_survey_report | 基本任务报告 PDF + LaTeX（.tex/.bib）+ 系统说明副本 |
| 04_evidence | 金标跑次验证 JSON / 评审摘要 |
| 05_compliance | API/数据/依赖/PRIOR_WORK 披露 |
| 06_route_a | Route A SPR + 解释文档 + 消融 + 稳定度摘要 |

门户：https://goaihz.com
"@ | Set-Content -Encoding UTF8 (Join-Path $PortalStage "README.md")

$OfficialZip = Join-Path $OutDir $OfficialName
New-ZipFromDir $PortalStage $OfficialZip
Write-Host "official=$OfficialZip SemiFinal=$SemiFinal"

# cleanup stages
Remove-Item $EvStage -Recurse -Force
Remove-Item $CodeStageRoot -Recurse -Force
Remove-Item $PortalStage -Recurse -Force

# ---- 5) Manifest ----
$manifest = @"
# Package manifest $Stamp

- **official (upload this):** $OfficialName
- docs (aux): $(Split-Path $DocsZip -Leaf)
- evidence (aux): $(Split-Path $EvZip -Leaf)
- code (aux): $(Split-Path $CodeZip -Leaf)

Naming: document/xiuding.md → AI4R_ALG_MAT_和昆仑.zip
Portal: https://goaihz.com
"@
$manifestPath = Join-Path $OutDir "MANIFEST_$Stamp.md"
$manifest | Set-Content -Encoding UTF8 $manifestPath
Write-Host "manifest=$manifestPath"
Write-Host "DONE"
