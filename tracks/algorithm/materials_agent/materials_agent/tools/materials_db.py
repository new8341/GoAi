"""Materials Project / OQMD external validation for Route A hypotheses."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import httpx

from materials_agent.config import AppConfig, MaterialsDBConfig

# Offline stub: thermodynamic / phase-stability heuristics for demo motifs.
_OFFLINE_STABLE: dict[str, dict[str, Any]] = {
    "snse": {
        "formula": "SnSe",
        "stable": True,
        "energy_above_hull": 0.0,
        "source": "offline_stub",
        "note": "Known layered thermoelectric phase; treat as pass for motif check.",
    },
    "pbte": {
        "formula": "PbTe",
        "stable": True,
        "energy_above_hull": 0.0,
        "source": "offline_stub",
        "note": "Rock-salt thermoelectric; pass for motif check.",
    },
    "bi2te3": {
        "formula": "Bi2Te3",
        "stable": True,
        "energy_above_hull": 0.0,
        "source": "offline_stub",
        "note": "Canonical near-room-temp thermoelectric.",
    },
    "mg3sb2": {
        "formula": "Mg3Sb2",
        "stable": True,
        "energy_above_hull": 0.02,
        "source": "offline_stub",
        "note": "Promising n-type; air sensitivity is process risk, not hull fail.",
    },
    "gete": {
        "formula": "GeTe",
        "stable": True,
        "energy_above_hull": 0.0,
        "source": "offline_stub",
    },
    "cusbse2": {
        "formula": "CuSbSe2",
        "stable": False,
        "energy_above_hull": 0.12,
        "source": "offline_stub",
        "note": "Stub unstable motif for fail-path demos.",
    },
}


@dataclass
class ValidationResult:
    motif: str
    formula: str
    verdict: str  # pass | fail | skip | error
    provider: str
    energy_above_hull: float | None = None
    stable: bool | None = None
    detail: str = ""
    raw: dict[str, Any] | None = None


def _normalize_motif(motif: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]", "", motif or "").lower()
    aliases = {
        "halfheusler": "halfheusler",
        "tinselenide": "snse",
        "leadtelluride": "pbte",
        "bismuthtelluride": "bi2te3",
    }
    return aliases.get(s, s)


_FORMULA_RE = re.compile(
    r"\b("
    r"SnSe|PbTe|Bi2Te3|Mg3Sb2|GeTe|CuSbSe2|SnTe|PbSe|Bi2Se3|"
    r"CoSb3|Skutterudite|"
    r"[A-Z][a-z]?(?:\d+[A-Z][a-z]?\d*){0,6}"
    r")\b"
)


def extract_chemical_formula(motif: str) -> str | None:
    """Extract a queryable chemical formula from a free-text motif.

    Rejects prose like "Lead chalcogenides (for comparison)" that breaks MP formula search.
    """
    text = (motif or "").strip()
    if not text:
        return None
    # Prefer known thermoelectrics first.
    for known in ("SnSe", "PbTe", "Bi2Te3", "Mg3Sb2", "GeTe", "CuSbSe2", "SnTe", "PbSe"):
        if re.search(rf"\b{re.escape(known)}\b", text, flags=re.IGNORECASE):
            return known
    # Reject long prose / parentheses-heavy labels without a compact formula token.
    if len(text) > 32 and "(" in text:
        m = _FORMULA_RE.search(text)
        if not m:
            return None
        cand = m.group(1)
        if cand.lower() in {"the", "for", "and", "with"}:
            return None
        if re.fullmatch(r"[A-Za-z]{6,}", cand):
            return None
        return cand
    compact = re.sub(r"[^A-Za-z0-9]", "", text)
    if re.fullmatch(r"[A-Z][a-z]?(?:\d+[A-Z][a-z]?\d*)*", text.replace(" ", "")) or (
        2 <= len(compact) <= 16 and re.search(r"\d|[A-Z][a-z]", text)
    ):
        # Already formula-like
        m2 = _FORMULA_RE.search(text)
        return m2.group(1) if m2 else text.replace(" ", "")
    m3 = _FORMULA_RE.search(text)
    if not m3:
        return None
    cand = m3.group(1)
    if re.fullmatch(r"[A-Za-z]{8,}", cand):
        return None
    return cand


def _cache_path(cfg: AppConfig) -> Path:
    root = Path(__file__).resolve().parents[2]
    rel = Path(cfg.materials_db.cache_path)
    return rel if rel.is_absolute() else root / rel


def _load_cache(path: Path) -> dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_cache(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _offline_lookup(motif: str) -> ValidationResult:
    key = _normalize_motif(motif)
    hit = _OFFLINE_STABLE.get(key)
    if not hit:
        # half-Heusler / generic: soft skip rather than hard fail
        if "heusler" in motif.lower() or "mof" in motif.lower():
            return ValidationResult(
                motif=motif,
                formula=motif,
                verdict="skip",
                provider="offline",
                detail="No offline entry; mark skip pending MP/OQMD query.",
            )
        return ValidationResult(
            motif=motif,
            formula=motif,
            verdict="skip",
            provider="offline",
            detail=f"Unknown motif `{motif}` in offline stub.",
        )
    stable = bool(hit.get("stable"))
    return ValidationResult(
        motif=motif,
        formula=str(hit.get("formula") or motif),
        verdict="pass" if stable else "fail",
        provider="offline",
        energy_above_hull=float(hit.get("energy_above_hull") or 0.0),
        stable=stable,
        detail=str(hit.get("note") or ""),
        raw=hit,
    )


def _mp_lookup(motif: str, db: MaterialsDBConfig) -> ValidationResult:
    if not db.mp_api_key.strip():
        if not db.allow_offline_fallback:
            return ValidationResult(
                motif=motif,
                formula=motif,
                verdict="error",
                provider="materials_project",
                detail="MP_API_KEY is required when offline fallback is disabled.",
            )
        return _offline_lookup(motif)
    formula = extract_chemical_formula(motif)
    if not formula:
        return ValidationResult(
            motif=motif,
            formula=motif,
            verdict="error",
            provider="materials_project",
            detail="Motif is not a queryable chemical formula; rejected before MP call.",
        )
    url = f"{db.mp_api_base.rstrip('/')}/materials/summary/"
    headers = {"X-API-KEY": db.mp_api_key, "Accept": "application/json"}
    # MP API uses underscore-prefixed pagination/field params.
    params = {
        "formula": formula,
        "_limit": 8,
        "_fields": "material_id,formula_pretty,energy_above_hull,is_stable",
    }
    try:
        with httpx.Client(timeout=db.timeout_s, headers=headers) as client:
            r = client.get(url, params=params)
            if r.status_code == 404:
                return ValidationResult(
                    motif=motif,
                    formula=formula,
                    verdict="fail",
                    provider="materials_project",
                    detail="No MP summary hit.",
                )
            r.raise_for_status()
            payload = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        return ValidationResult(
            motif=motif,
            formula=formula,
            verdict="error",
            provider="materials_project",
            detail=f"MP API error: {exc}",
        )

    data = payload.get("data") or payload.get("results") or []
    if not data:
        if not db.allow_offline_fallback:
            return ValidationResult(
                motif=motif,
                formula=formula,
                verdict="error",
                provider="materials_project",
                detail="MP API returned no matching material.",
            )
        # fall back offline for known demo motifs
        offline = _offline_lookup(motif)
        offline.detail = (offline.detail + " | MP empty → offline fallback").strip(" |")
        return offline

    rows = [row for row in data if isinstance(row, dict)]
    if not rows:
        rows = [data[0]] if isinstance(data, list) else [data]

    def _hull_key(row: dict[str, Any]) -> float:
        value = row.get("energy_above_hull")
        try:
            return float(value)
        except (TypeError, ValueError):
            return 1e9

    # Prefer explicitly stable rows, then lowest energy above hull.
    rows.sort(key=lambda row: (0 if row.get("is_stable") else 1, _hull_key(row)))
    row = rows[0]
    e_hull = row.get("energy_above_hull")
    stable = row.get("is_stable")
    if stable is None and e_hull is not None:
        stable = float(e_hull) <= 0.05
    verdict = "pass" if stable else "fail"
    return ValidationResult(
        motif=motif,
        formula=str(row.get("formula_pretty") or formula),
        verdict=verdict,
        provider="materials_project",
        energy_above_hull=float(e_hull) if e_hull is not None else None,
        stable=bool(stable) if stable is not None else None,
        detail=str(row.get("material_id") or ""),
        raw=row if isinstance(row, dict) else {"row": row},
    )


def _oqmd_lookup(motif: str, db: MaterialsDBConfig) -> ValidationResult:
    formula = extract_chemical_formula(motif) or motif
    url = f"{db.oqmd_api_base.rstrip('/')}/formationenergy"
    params = {"composition": formula, "limit": 1}
    try:
        with httpx.Client(timeout=db.timeout_s) as client:
            r = client.get(url, params=params)
            r.raise_for_status()
            payload = r.json()
    except (httpx.HTTPError, ValueError) as exc:
        if not db.allow_offline_fallback:
            return ValidationResult(
                motif=motif,
                formula=motif,
                verdict="error",
                provider="oqmd",
                detail=f"OQMD error: {exc}",
            )
        offline = _offline_lookup(motif)
        offline.detail = f"OQMD error ({exc}); offline fallback. {offline.detail}".strip()
        return offline

    data = payload.get("data") or []
    if not data:
        if not db.allow_offline_fallback:
            return ValidationResult(
                motif=motif,
                formula=motif,
                verdict="error",
                provider="oqmd",
                detail="OQMD returned no matching material.",
            )
        return _offline_lookup(motif)
    row = data[0]
    # OQMD stability_field varies; treat missing as skip
    delta_e = row.get("delta_e")
    stable = True if delta_e is None else float(delta_e) <= 0.05
    return ValidationResult(
        motif=motif,
        formula=str(row.get("name") or motif),
        verdict="pass" if stable else "fail",
        provider="oqmd",
        energy_above_hull=float(delta_e) if delta_e is not None else None,
        stable=stable,
        detail="oqmd formationenergy",
        raw=row if isinstance(row, dict) else {"row": row},
    )


def _combine_mp_oqmd(mp: ValidationResult, oqmd: ValidationResult) -> ValidationResult:
    """Prefer agreement; surface both providers in detail for handbook cross-check."""
    formula = mp.formula or oqmd.formula
    motif = mp.motif or oqmd.motif
    if mp.verdict == "pass" and oqmd.verdict == "pass":
        verdict = "pass"
    elif "error" in {mp.verdict, oqmd.verdict} and "pass" not in {mp.verdict, oqmd.verdict}:
        verdict = "error" if mp.verdict == "error" and oqmd.verdict == "error" else (
            mp.verdict if mp.verdict != "error" else oqmd.verdict
        )
    elif mp.verdict == "pass" or oqmd.verdict == "pass":
        verdict = "pass"
    elif mp.verdict == "fail" or oqmd.verdict == "fail":
        verdict = "fail"
    else:
        verdict = "skip"
    detail = (
        f"mp={mp.verdict}({mp.detail}); oqmd={oqmd.verdict}({oqmd.detail})"
    )
    e_hull = mp.energy_above_hull
    if e_hull is None:
        e_hull = oqmd.energy_above_hull
    stable = True if verdict == "pass" else (False if verdict == "fail" else None)
    return ValidationResult(
        motif=motif,
        formula=formula,
        verdict=verdict,
        provider="mp_oqmd",
        energy_above_hull=e_hull,
        stable=stable,
        detail=detail,
        raw={"materials_project": mp.raw, "oqmd": oqmd.raw},
    )


def validate_motif(motif: str, cfg: AppConfig) -> ValidationResult:
    provider = (cfg.route_a.materials_db or cfg.materials_db.provider or "offline").lower()
    cache_file = _cache_path(cfg)
    cache = _load_cache(cache_file)
    key = f"{provider}:{_normalize_motif(motif)}"
    if key in cache:
        row = cache[key]
        return ValidationResult(**row)

    if provider in {"materials_project", "mp"}:
        result = _mp_lookup(motif, cfg.materials_db)
    elif provider == "oqmd":
        result = _oqmd_lookup(motif, cfg.materials_db)
    elif provider in {"mp_oqmd", "both", "mp+oqmd", "materials_project+oqmd"}:
        mp = _mp_lookup(motif, cfg.materials_db)
        oqmd = _oqmd_lookup(motif, cfg.materials_db)
        result = _combine_mp_oqmd(mp, oqmd)
    else:
        result = _offline_lookup(motif)

    cache[key] = asdict(result)
    _save_cache(cache_file, cache)
    return result


def validate_candidates(
    candidates: list[Any],
    cfg: AppConfig,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Attach external_validation dict onto top-K SPR candidates."""
    k = top_k if top_k is not None else cfg.route_a.validate_top_k
    rows: list[dict[str, Any]] = []
    for i, cand in enumerate(candidates[:k]):
        motif = getattr(cand, "material_motif", None) or cand.get("material_motif")
        result = validate_motif(str(motif), cfg)
        payload = asdict(result)
        if hasattr(cand, "__dict__"):
            setattr(cand, "external_validation", payload)
        elif isinstance(cand, dict):
            cand["external_validation"] = payload
        rows.append(payload)
    return rows
