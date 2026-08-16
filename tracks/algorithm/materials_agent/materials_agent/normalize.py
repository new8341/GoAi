from __future__ import annotations

import re
from typing import Iterable


_PROP_ALIASES = {
    "figure of merit": "ZT",
    "zt": "ZT",
    "z t": "ZT",
    "seebeck": "Seebeck coefficient",
    "seebeck coefficient": "Seebeck coefficient",
    "thermal conductivity": "thermal conductivity",
    "lattice thermal conductivity": "lattice thermal conductivity",
    "electrical conductivity": "electrical conductivity",
    "power factor": "power factor",
    "band gap": "band gap",
    "mobility": "carrier mobility",
    "carrier mobility": "carrier mobility",
    "stability": "stability",
}

_METHOD_ALIASES = {
    "density functional": "DFT",
    "dft": "DFT",
    "machine learning": "machine learning",
    "neural network": "machine learning",
    "molecular dynamics": "molecular dynamics",
    "md": "molecular dynamics",
    "spark plasma": "spark plasma sintering",
    "spark plasma sintering": "spark plasma sintering",
    "synthesis": "synthesis",
    "xrd": "XRD",
    "sem": "SEM",
    "tem": "TEM",
    "hydrothermal": "hydrothermal",
    "sol gel": "sol-gel",
    "sol-gel": "sol-gel",
}


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def normalize_property(name: str, ontology: dict | None = None) -> str:
    key = _norm_key(name)
    if ontology:
        for p in ontology.get("properties") or []:
            if _norm_key(str(p)) == key:
                return str(p)
    return _PROP_ALIASES.get(key, name.strip())


def normalize_method(name: str, ontology: dict | None = None) -> str:
    key = _norm_key(name)
    if ontology:
        for m in ontology.get("methods") or []:
            if _norm_key(str(m)) == key or key in _norm_key(str(m)):
                return str(m)
    return _METHOD_ALIASES.get(key, name.strip())


def dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        s = (x or "").strip()
        if not s:
            continue
        k = _norm_key(s)
        if k in seen:
            continue
        seen.add(k)
        out.append(s)
    return out


def normalize_material(name: str, ontology: dict | None = None) -> str:
    s = (name or "").strip()
    if not s:
        return s
    # unify half-Heusler spelling
    if re.search(r"half[\s-]*heusler", s, re.I):
        return "half-Heusler"
    if ontology:
        for m in ontology.get("materials_examples") or []:
            if _norm_key(str(m)) == _norm_key(s):
                return str(m)
    return s
