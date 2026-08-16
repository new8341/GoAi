from materials_agent.agents.evidence import quote_in_source
from materials_agent.models import EvidenceProvenance


def test_quote_in_source_checks_offset() -> None:
    source = "A valid evidence sentence is here."
    quote = "valid evidence"
    start = source.index(quote)
    provenance = EvidenceProvenance(char_start=start, char_end=start + len(quote))

    assert quote_in_source(quote, source, provenance)
    assert not quote_in_source(
        quote,
        source,
        EvidenceProvenance(char_start=0, char_end=len(quote)),
    )
