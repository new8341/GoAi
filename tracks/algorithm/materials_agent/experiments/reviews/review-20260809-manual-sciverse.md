# Gap review 2026-08-09

Reviewer: Auto (UI + artifacts manual check)
Config: configs/production_sciverse.yaml
Run: `outputs/production_sciverse` (UI: production_sciverse ★)
production_verification: **PASS**
Also checked latest UI job: `outputs/user_jobs/20260808T164059Z-f0ef22cf` (sciverse + Route A)

## Automation / UI checklist

| Item | production_sciverse | Pass? |
|------|---------------------|-------|
| verify status | PASS (parsed 4/5, fulltext spans 8) | yes |
| papers ≥ 5 | 5 | yes (edge) |
| gaps ≥ 1 | 2 | yes |
| fulltext coverage | 4/5 | yes |
| consistency | ok | yes |
| Sciverse audit (no OpenAlex fallback) | `5 papers (raw=10)`, mode=meta, errors=[] | yes |
| metadata quality | 3/5 titles are DOI placeholders; years missing | **no** |
| Gap evidence scientific relevance | see below | **no** |

## Gap quote reverse-check

All sampled quotes **are substrings** of the cited `evidence_chunks` (provenance mechanically OK).  
Scientific relevance of those quotes vs Gap claim: **mostly FAIL**.

| gap_id | type | quote⊂source | claim-aligned? | notes |
|--------|------|--------------|----------------|-------|
| gap-limitations | underexplored | yes (4/4) | **no** | e0–e1 = Creative Commons / peer-review boilerplate; e2 = closing Experimental Section; e3 = κ_L formula (method, not a limitation cluster). Title/description overclaim “open limitations”. Next-step is template-generic. |
| gap-temporal-SnSe | contradiction | yes (4/4) | **no** | Evidence is almost all from **2020** paper only; no paired conflicting claim from 2025 Zenodo item. Quotes include scattering formulas, NP volume-fraction finding, references block, title-page header — **not** an era-to-era contradiction table. |

Overall (scientific): **revise evidence filters** — reject both Gaps as currently evidenced; keep mechanical PASS as infrastructure evidence only.

## Latest UI job (20260808T164059Z)

| Item | Value | Pass? |
|------|-------|-------|
| Runtime | ~71 s | suspiciously short for production fulltext |
| papers / fulltext | 3 / 1 | below sciverse guide ≥5 / half fulltext |
| gaps | same template ids (`gap-limitations`, `gap-temporal-SnSe`) | weak specificity |
| Route A | 12 candidates, scores ~0.11–0.19, novelty=known, external=`offline_stub` | not competition-grade MP validation |
| production_verification.json | absent on this job dir | not a ★ PASS run |

Do **not** treat this job as submission evidence; use `production_sciverse` or re-run full OpenAlex `production` (10 papers, PASS) after Gap filter fixes.

## Follow-up (code fix 2026-08-09)

Evidence filter landed in `materials_agent/agents/evidence_selector.py`:
- drop Creative Commons / peer-review / references boilerplate
- ground `gap-limitations` from extracted limitation sentences
- require dual-era evidence for temporal contradictions

Offline re-ground on this run’s chunks: limitations boilerplate 3→0; temporal papers become early+recent.
**Re-run** `production` / `production_sciverse` (or UI Start) to refresh `gaps.json` / report artifacts.
