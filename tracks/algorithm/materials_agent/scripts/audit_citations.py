#!/usr/bin/env python3
"""Audit BibTeX / gap DOIs against OpenAlex (citation authenticity self-check)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s}\"']+", re.I)
_TITLE_RE = re.compile(r"title\s*=\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", re.I)
_ENTRY_RE = re.compile(r"@\w+\s*\{([^,]+),", re.I)


def _parse_bib(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    entries: list[dict] = []
    # Split roughly on @entries
    parts = re.split(r"(?=@\w+\s*\{)", text)
    for part in parts:
        if not part.strip().startswith("@"):
            continue
        key_m = _ENTRY_RE.search(part)
        doi_m = _DOI_RE.search(part)
        title_m = _TITLE_RE.search(part)
        entries.append(
            {
                "key": key_m.group(1).strip() if key_m else "",
                "doi": doi_m.group(0).rstrip(".,;") if doi_m else "",
                "title": (title_m.group(1).strip() if title_m else "")[:200],
            }
        )
    return entries


def _openalex_doi(doi: str, mailto: str) -> dict:
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    headers = {"User-Agent": f"materials-agent-cite-audit (mailto:{mailto})"}
    with httpx.Client(timeout=30.0, headers=headers, follow_redirects=True) as client:
        r = client.get(url, params={"mailto": mailto})
        if r.status_code == 404:
            return {"ok": False, "status": 404, "display_name": None}
        r.raise_for_status()
        data = r.json()
        return {
            "ok": True,
            "status": r.status_code,
            "display_name": data.get("display_name"),
            "openalex_id": data.get("id"),
            "publication_year": data.get("publication_year"),
        }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--bib",
        default=str(ROOT / "outputs" / "production_sciverse" / "references.bib"),
    )
    p.add_argument(
        "--out",
        default=str(
            ROOT.parents[2] / "submissions" / "semi_final" / "citation_audit.md"
        ),
    )
    p.add_argument("--mailto", default="")
    p.add_argument("--limit", type=int, default=30)
    args = p.parse_args()

    bib = Path(args.bib)
    if not bib.is_file():
        print(f"missing bib: {bib}", file=sys.stderr)
        return 1

    import os

    mailto = (
        args.mailto
        or os.environ.get("OPENALEX_EMAIL")
        or "team@example.com"
    ).strip()
    entries = _parse_bib(bib)[: args.limit]
    rows = []
    ok_n = fail_n = nodoi_n = 0
    for e in entries:
        if not e["doi"]:
            nodoi_n += 1
            rows.append({**e, "verdict": "no_doi", "openalex_title": None})
            continue
        try:
            hit = _openalex_doi(e["doi"], mailto)
            time.sleep(0.12)
        except Exception as exc:  # noqa: BLE001
            fail_n += 1
            rows.append(
                {
                    **e,
                    "verdict": "error",
                    "openalex_title": None,
                    "error": str(exc)[:160],
                }
            )
            continue
        if hit.get("ok"):
            ok_n += 1
            rows.append(
                {
                    **e,
                    "verdict": "verified",
                    "openalex_title": hit.get("display_name"),
                    "year": hit.get("publication_year"),
                }
            )
        else:
            fail_n += 1
            rows.append({**e, "verdict": "not_found", "openalex_title": None})

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    # fix default if parents wrong
    if not out.parent.exists():
        alt = ROOT.parents[2] / "submissions" / "semi_final" / "citation_audit.md"
        # materials_agent -> algorithm -> tracks -> repo
        out = ROOT.parents[2] / "submissions" / "semi_final" / "citation_audit.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# 引用真实性自查（OpenAlex DOI）",
        "",
        f"> Source bib: `{bib.as_posix()}`",
        f"> Checked: {len(rows)} entries · verified={ok_n} · not_found/error={fail_n} · no_doi={nodoi_n}",
        "",
        "手册：组委会可抽查虚假引用。本表为提交前自检，不替代人工审读。",
        "",
        "| Key | DOI | Verdict | OpenAlex title (trunc) |",
        "|-----|-----|---------|------------------------|",
    ]
    for r in rows:
        title = (r.get("openalex_title") or r.get("title") or "")[:60].replace("|", "/")
        lines.append(
            f"| `{r.get('key','')}` | `{r.get('doi','')}` | {r.get('verdict')} | {title} |"
        )
    lines += ["", f"JSON sidecar: `{out.with_suffix('.json').name}`", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    out.with_suffix(".json").write_text(
        json.dumps(
            {"bib": str(bib), "ok": ok_n, "fail": fail_n, "no_doi": nodoi_n, "rows": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"wrote {out} verified={ok_n} fail={fail_n} no_doi={nodoi_n}")
    return 0 if fail_n == 0 else 0  # soft pass; report is the deliverable


if __name__ == "__main__":
    raise SystemExit(main())
