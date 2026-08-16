"""GROBID TEI parser adapter used for scientific-paper structure and provenance."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import httpx

from materials_agent.config import ParserConfig
from materials_agent.tools.parsers.base import ParsedDocument

_TEI = {"tei": "http://www.tei-c.org/ns/1.0"}


def _tei_to_text_and_sections(tei: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Project TEI body paragraphs to text while retaining section character ranges."""
    try:
        root = ElementTree.fromstring(tei)
    except ElementTree.ParseError:
        return "", []
    chunks: list[str] = []
    sections: list[tuple[str, int, int]] = []
    current_section = "Body"
    start = 0
    for node in root.findall(".//tei:text/tei:body//*", _TEI):
        tag = node.tag.rsplit("}", 1)[-1]
        content = " ".join("".join(node.itertext()).split())
        if not content:
            continue
        if tag == "head":
            if chunks:
                sections.append((current_section, start, len("\n\n".join(chunks))))
            current_section = content[:200]
            start = len("\n\n".join(chunks))
        elif tag == "p":
            chunks.append(content)
    text = "\n\n".join(chunks)
    if text:
        sections.append((current_section, start, len(text)))
    return text, sections


def parse_with_grobid(pdf_path: Path, output_dir: Path, cfg: ParserConfig) -> ParsedDocument:
    """POST a PDF to GROBID's fulltext endpoint and save raw TEI."""
    output_dir.mkdir(parents=True, exist_ok=True)
    endpoint = f"{cfg.grobid_url.rstrip('/')}/api/processFulltextDocument"
    timeout = httpx.Timeout(
        float(cfg.grobid_timeout_s or 120),
        connect=10.0,
        read=float(cfg.grobid_timeout_s or 120),
        write=30.0,
        pool=10.0,
    )
    try:
        with pdf_path.open("rb") as handle, httpx.Client(timeout=timeout) as client:
            response = client.post(
                endpoint,
                files={"input": (pdf_path.name, handle, "application/pdf")},
                headers={"Accept": "application/xml"},
            )
            response.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        return ParsedDocument(parser="grobid", error=f"GROBID error: {exc}")

    tei = response.text
    tei_path = output_dir / "grobid.tei.xml"
    tei_path.write_text(tei, encoding="utf-8")
    text, sections = _tei_to_text_and_sections(tei)
    if len(text) < 80:
        return ParsedDocument(
            parser="grobid",
            output_paths={"tei": str(tei_path)},
            error="GROBID TEI has no usable body text",
        )
    return ParsedDocument(
        text=text,
        parser="grobid",
        sections=sections,
        output_paths={"tei": str(tei_path)},
    )
