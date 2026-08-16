"""Hugging Face Sci-Base (opendatalab/Sci-Base) access for literature retrieval.

The full dataset is multi-TB. This client prefers a local materials cache
(JSONL) and only streams from HF when the cache is missing or a rebuild is
requested. Source label for evidence chains: ``scibase``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Iterator

from materials_agent.config import AppConfig
from materials_agent.models import Paper

DEFAULT_DATASET = "opendatalab/Sci-Base"
DEFAULT_CONFIG = "paper"
DEFAULT_CACHE = "data/scibase/materials_cache.jsonl"

_MATERIALS_CAT = re.compile(
    r"materials?\s*science|material|thermoelectric|chemistry|physics",
    re.I,
)


def resolve_scibase_cache_path(cfg: AppConfig) -> Path:
    raw = (getattr(cfg.retrieval, "scibase_cache_path", "") or DEFAULT_CACHE).strip()
    path = Path(raw)
    root = Path(__file__).resolve().parents[2]
    if not path.is_absolute():
        path = root / path
    if path.is_file():
        return path
    alt = root / "experiments" / "scibase" / "materials_cache.jsonl"
    if alt.is_file():
        return alt
    return path


def _author_list(author: Any) -> list[str]:
    if author is None:
        return []
    if isinstance(author, list):
        return [str(a).strip() for a in author if str(a).strip()]
    text = str(author).strip()
    if not text:
        return []
    for sep in ("|", ";", "\n"):
        if sep in text:
            return [p.strip() for p in text.split(sep) if p.strip()]
    return [text]


def _content_list_text(content_list: Any, max_chars: int = 12000) -> str | None:
    if not content_list:
        return None
    parts: list[str] = []
    total = 0
    for item in content_list:
        if isinstance(item, dict):
            chunk = (
                item.get("text")
                or item.get("table_body")
                or item.get("code_body")
                or ""
            )
        else:
            chunk = str(item) if item is not None else ""
        chunk = str(chunk).strip()
        if not chunk:
            continue
        parts.append(chunk)
        total += len(chunk)
        if total >= max_chars:
            break
    if not parts:
        return None
    return "\n".join(parts)[:max_chars]


def row_to_paper(row: dict[str, Any], *, query_tag: str = "") -> Paper | None:
    title = (row.get("title") or "").strip()
    if not title:
        return None
    doi = (row.get("doi") or "").strip() or None
    sha = (row.get("sha256") or "").strip()
    pid = sha[:20] if sha else None
    if not pid and doi:
        pid = "doi:" + re.sub(r"[^a-zA-Z0-9._/-]+", "_", doi)[:80]
    if not pid:
        pid = "scibase:" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]

    abstract = (row.get("abstract") or "").strip() or None
    full_text = _content_list_text(row.get("content_list"))
    category = str(row.get("sci_category") or "")
    is_oa = bool(row.get("is_oa")) if row.get("is_oa") is not None else True

    return Paper(
        id=pid,
        title=title,
        year=None,
        doi=doi,
        abstract=abstract,
        full_text=full_text,
        authors=_author_list(row.get("author")),
        cited_by=0,
        venue=None,
        url=f"https://doi.org/{doi}" if doi else None,
        oa_url=f"https://doi.org/{doi}" if doi and is_oa else None,
        fulltext_url=None,
        oa_status="oa" if is_oa else None,
        oa_license="see-original-oa",
        concepts=[c.strip() for c in category.split("/") if c.strip()][:8],
        source="scibase",
        query_tag=query_tag,
        fulltext_source="scibase_content_list" if full_text else "",
        raw={
            "dataset": DEFAULT_DATASET,
            "hf_config": DEFAULT_CONFIG,
            "sha256": sha or None,
            "sci_category": category,
            "language": row.get("language"),
            "is_oa": is_oa,
        },
    )


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def score_row(row: dict[str, Any], query: str) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    blob = f"{row.get('title') or ''} {row.get('abstract') or ''} {row.get('sci_category') or ''}"
    doc = _tokens(blob)
    if not doc:
        return 0.0
    return len(q & doc) / len(q)


def category_ok(row: dict[str, Any], substrings: Iterable[str] | None) -> bool:
    cat = str(row.get("sci_category") or "")
    if not substrings:
        return bool(_MATERIALS_CAT.search(cat)) or True
    low = cat.lower()
    return any(s.lower() in low for s in substrings if s)


def load_cache_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def write_cache_rows(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def search_cache(
    rows: list[dict[str, Any]],
    queries: list[str],
    *,
    top_k: int,
    category_substrings: list[str] | None,
) -> list[Paper]:
    scored: list[tuple[float, dict[str, Any], str]] = []
    for row in rows:
        if not category_ok(row, category_substrings):
            continue
        best_q = queries[0] if queries else ""
        best = 0.0
        for q in queries:
            s = score_row(row, q)
            if s > best:
                best = s
                best_q = q
        if best <= 0:
            continue
        scored.append((best, row, best_q))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[Paper] = []
    seen: set[str] = set()
    for score, row, q in scored:
        paper = row_to_paper(row, query_tag=q)
        if paper is None or paper.id in seen:
            continue
        paper.relevance_score = round(float(score), 4)
        seen.add(paper.id)
        out.append(paper)
        if len(out) >= top_k:
            break
    return out


def iter_hf_stream(
    *,
    dataset: str = DEFAULT_DATASET,
    config: str = DEFAULT_CONFIG,
    max_scan: int,
) -> Iterator[dict[str, Any]]:
    try:
        from datasets import load_dataset
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Sci-Base streaming requires `pip install datasets pyarrow`. "
            "Or use a prebuilt materials_cache.jsonl."
        ) from exc

    ds = load_dataset(dataset, config, split="train", streaming=True)
    for i, row in enumerate(ds):
        if i >= max_scan:
            break
        if hasattr(row, "items"):
            yield dict(row)
        else:
            yield dict(row)


def build_materials_cache(
    out_path: Path,
    *,
    dataset: str = DEFAULT_DATASET,
    config: str = DEFAULT_CONFIG,
    max_scan: int = 8000,
    max_keep: int = 400,
    category_substrings: list[str] | None = None,
    keyword_boost: str = "SnSe thermoelectric vacancy thermal",
) -> dict[str, Any]:
    """Stream HF Sci-Base and keep materials-relevant rows (title/abstract only)."""
    cats = category_substrings or [
        "Materials",
        "Chemistry",
        "Physics",
        "Energy",
    ]
    kept: list[tuple[float, dict[str, Any]]] = []
    scanned = 0
    for row in iter_hf_stream(dataset=dataset, config=config, max_scan=max_scan):
        scanned += 1
        if not category_ok(row, cats):
            continue
        # Slim row for cache (drop huge content_list bodies in bulk cache;
        # keep a short preview for evidence when present).
        preview = _content_list_text(row.get("content_list"), max_chars=2500)
        slim = {
            "title": row.get("title"),
            "abstract": row.get("abstract"),
            "author": row.get("author"),
            "doi": row.get("doi"),
            "is_oa": row.get("is_oa"),
            "language": row.get("language"),
            "sci_category": row.get("sci_category"),
            "sha256": row.get("sha256"),
            "content_list": (
                [{"text": preview, "page_idx": "0"}] if preview else []
            ),
        }
        s = score_row(slim, keyword_boost) + (
            0.15 if _MATERIALS_CAT.search(str(slim.get("sci_category") or "")) else 0.0
        )
        if s < 0.05 and "material" not in str(slim.get("sci_category") or "").lower():
            continue
        kept.append((s, slim))
        if len(kept) >= max_keep * 3:
            kept.sort(key=lambda x: x[0], reverse=True)
            kept = kept[: max_keep * 2]

    kept.sort(key=lambda x: x[0], reverse=True)
    rows = [r for _, r in kept[:max_keep]]
    n = write_cache_rows(out_path, rows)
    return {
        "scanned": scanned,
        "kept": n,
        "cache_path": str(out_path),
        "dataset": dataset,
        "config": config,
    }
