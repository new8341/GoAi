"""Title hygiene: reject filesystem stems and backfill from TEI / fulltext."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

from materials_agent.agents.evidence_selector import is_boilerplate_text
from materials_agent.models import Paper

_TEI = {"tei": "http://www.tei-c.org/ns/1.0"}
_PLACEHOLDER = re.compile(r"(?i)^\s*(sv[-_ ]?paper|svc[-_ ])")


def is_placeholder_title(title: str | None, paper_id: str = "") -> bool:
    text = (title or "").strip()
    if not text:
        return True
    if _PLACEHOLDER.search(text):
        return True
    pid = (paper_id or "").strip()
    if pid and text.replace(" ", "_") == pid.replace(" ", "_"):
        return True
    if text.startswith(pid) and pid.startswith("SV-"):
        return True
    return False


def title_from_tei_xml(tei: str) -> str | None:
    try:
        root = ElementTree.fromstring(tei)
    except ElementTree.ParseError:
        return None
    for node in root.findall(".//{http://www.tei-c.org/ns/1.0}titleStmt/{http://www.tei-c.org/ns/1.0}title"):
        text = " ".join("".join(node.itertext()).split()).strip()
        if len(text) >= 12 and not is_placeholder_title(text):
            return text[:220]
    for node in root.findall(".//tei:titleStmt/tei:title", _TEI):
        text = " ".join("".join(node.itertext()).split()).strip()
        if len(text) >= 12 and not is_placeholder_title(text):
            return text[:220]
    return None


def title_from_tei_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    return title_from_tei_xml(path.read_text(encoding="utf-8", errors="ignore"))


def title_from_fulltext(full_text: str) -> str | None:
    for line in (full_text or "").splitlines()[:80]:
        line = line.strip()
        if len(line) < 20 or len(line) > 220:
            continue
        if is_boilerplate_text(line):
            continue
        if re.search(
            r"creative commons|doi\.org|correspondence|keywords|abstract",
            line,
            re.I,
        ):
            continue
        return line[:220]
    return None


def backfill_paper_title(paper: Paper, tei_path: Path | None = None) -> bool:
    """Replace placeholder / empty titles. Returns True if title changed."""
    if not is_placeholder_title(paper.title, paper.id):
        return False
    new_title = None
    if tei_path is not None:
        new_title = title_from_tei_path(tei_path)
    if not new_title:
        new_title = title_from_fulltext(paper.full_text or "")
    if not new_title:
        return False
    paper.title = new_title
    return True
