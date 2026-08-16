# Hybrid full-text evidence-chain dependencies

## Profiles

| Profile | Required services | Purpose |
|---|---|---|
| `demo_local.yaml` | None | Deterministic smoke test over bundled local papers. |
| `default.yaml` | OpenAlex optional; no parser required | Metadata and abstract-first development. |
| `production.yaml` | OpenAlex, Unpaywall, **GROBID**, Qdrant | OA PDF acquisition and provenance-backed Gap evidence. MinerU is **optional** (not the default primary). |
| `production_sciverse.yaml` | Sciverse token (+ OpenAlex fallback), GROBID, Qdrant | Competition-recommended Sciverse meta/semantic search. |
| `production_sciverse_scibase.yaml` | Sciverse + **Sci-Base** materials cache | Handbook corpus: HF `opendatalab/Sci-Base` enrichment; evidence DB labels `sciverse`/`scibase`. |
| `production_semantic_scholar.yaml` | Semantic Scholar key (+ OpenAlex fallback), parsers as configured | Optional second retrieval backend (`S2_API_KEY`). |

## External resources (access + versions)

| Resource | How to obtain | Pinned / disclosed version | Used in |
|---|---|---|---|
| Sciverse API | Register at https://sciverse.opendatalab.com / https://sciverse.space → Bearer `SCIVERSE_API_TOKEN` | Client: repo `SciverseRetriever`; disclose token scope in submission. **MCP/Skill 接入为手册鼓励项**（当前 REST + audit 证据链） | `production_sciverse*` |
| Sci-Base | Hugging Face [`opendatalab/Sci-Base`](https://huggingface.co/datasets/opendatalab/Sci-Base) | Prefer local `data/scibase/materials_cache.jsonl` (built via `scripts/build_scibase_cache.py`); full dump is multi-TB. License: CC-BY-4.0 structure + original OA licenses. Cite `@misc{scibase2026,...}`. | `production_sciverse_scibase` / backend `scibase` |
| OpenAlex | https://openalex.org ; set `OPENALEX_EMAIL` | Public REST API | fallback / `production.yaml` |
| Unpaywall | https://unpaywall.org ; set `UNPAYWALL_EMAIL` | Public REST API | OA PDF URL resolution |
| Materials Project | https://materialsproject.org → `MP_API_KEY` | `mp-api` client per `requirements.txt` | Route A external validate |
| OQMD | https://oqmd.org (optional offline/online) | As configured in `materials_db` | Route A optional |
| GROBID | Docker image | **`grobid/grobid:0.8.0`** (`docker-compose.yml`) | production fulltext |
| Qdrant | Docker image | **`qdrant/qdrant:v1.13.2`** | evidence index |
| MinerU | Optional local install | See profile; not primary in production | optional parser |
| LLM (OpenAI-compatible) | `OPENAI_API_KEY` + `OPENAI_BASE_URL` + `OPENAI_MODEL` | Recorded in `external_versions.json` (key redacted) | rewrite/extract/gap/Route A |

Each survey run should include **`external_versions.json`** (via pipeline save or `scripts/dump_external_versions.py`).

## Survey report deliverables (handbook A04)

| Artifact | Generator |
|---|---|
| `report.md` | pipeline reporter (includes **Database** labels per Gap/claim) |
| `report.tex` + `references.bib` | `scripts/export_survey_latex.py` / pipeline save |
| `report.pdf` | optional: `tectonic` or `pdflatex`+`bibtex` on the `.tex` |

## Install

```bash
pip install -r requirements.txt
pip install ".[scibase]"   # datasets + pyarrow for HF Sci-Base cache builds
docker compose up -d grobid qdrant
```

Sci-Base materials cache:

```bash
py -3 scripts/build_scibase_cache.py --max-scan 5000 --max-keep 200
# then use configs/production_sciverse_scibase.yaml
```

Current production profile uses **GROBID as primary parser** (`secondary: none`) for Windows stability.
Handbook-recommended **MinerU** remains supported as optional primary (`parsers.primary: mineru`); Sci-Base rows already carry MinerU-parsed `content_list`. Disclose in submissions: production gold = GROBID; Sci-Base corpus = MinerU-parsed OA foundation.


## Environment and data policy

- `OPENALEX_EMAIL` and `UNPAYWALL_EMAIL` must be real team contact addresses.
- PDFs are only downloaded through OpenAlex/Unpaywall OA URLs; the agent does
  not bypass publisher paywalls.
- Retain the OA URL, license, version, retrieval time, and SHA-256 hash in the
  output manifest before using a document as production evidence.
- `OPENAI_API_KEY`, `CURSOR_API_KEY`, `MP_API_KEY`, `QDRANT_API_KEY`, and
  `SCIVERSE_API_TOKEN` are optional and must never be committed.
- Sciverse: obtain a Bearer token at https://sciverse.space; see
  `docs/文献库获取与缺口.md`. Without a token, `backend: sciverse` falls back
  to OpenAlex.
- The optional Cursor SDK backend requires `pip install ".[cursor-sdk]"`,
  `LLM_PROVIDER=cursor_sdk`, `CURSOR_API_KEY`, and a configured
  `CURSOR_WORKSPACE`. It runs local Cursor agents and is a commercial,
  closed-model dependency; retain a non-Cursor fallback for reproducible
  evaluation and disclose scope, cost, permissions, and migration impact.

## Degradation behavior

| Missing component | Behavior |
|---|---|
| MinerU / GROBID | Parsing is recorded as failed; production verifier does not pass. |
| Qdrant | Pipeline uses the file evidence index; audit records the actual backend. |
| Qdrant panic `unexpected entry in wal` | Usually `*.baiduyun.uploading.cfg` from Baidu Netdisk sync; delete those sidecars and restart the container. |
| Unpaywall response | Existing OpenAlex OA URL may still be used; no non-OA scrape occurs. |
| No OA PDF | Abstract fallback is allowed only outside the strict production profile. |
| Cursor SDK local bridge failure (e.g. Windows `WinError 10038`) | Calls are audited as `cursor_sdk` errors; if `OPENAI_API_KEY` is set, the client automatically falls back to the OpenAI-compatible API. |
| No Sciverse token / Sciverse API error | `SciverseRetriever` audits and falls back to OpenAlex. |
| No Sci-Base cache / streaming off | `SciBaseRetriever` fails when `allow_backend_fallback: false`; hybrid keeps Sciverse hits and audits enrich skip. |

## Local MinerU models (Windows)

```powershell
$env:MINERU_MODEL_SOURCE='local'
$env:HF_HUB_DISABLE_SYMLINKS='1'
# models live under data/models/PDF-Extract-Kit-1.0 ; mineru.json model-source=local
```

Production config sets `fulltext.allow_text_cache: false` so demo `.txt` caches cannot satisfy `verify_production.py`.

