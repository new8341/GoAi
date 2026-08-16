"""Optional full-text parser adapters."""

from materials_agent.tools.parsers.grobid_parser import parse_with_grobid
from materials_agent.tools.parsers.mineru_parser import parse_with_mineru

__all__ = ["parse_with_grobid", "parse_with_mineru"]
