"""OA URL normalization and rejection policy."""

from materials_agent.models import Paper
from materials_agent.tools.oa_download import (
    normalize_oa_url,
    resolve_oa_url,
    url_rejection_reason,
)


def test_normalize_osti_biblio_to_servlet() -> None:
    assert (
        normalize_oa_url("https://www.osti.gov/biblio/1775445")
        == "https://www.osti.gov/servlets/purl/1775445"
    )


def test_normalize_pmc_to_europepmc_pdf() -> None:
    assert (
        normalize_oa_url("https://www.ncbi.nlm.nih.gov/pmc/articles/8290941")
        == "https://europepmc.org/articles/pmc8290941?pdf=render"
    )


def test_reject_sciencedirect_abstract() -> None:
    url = "https://www.sciencedirect.com/science/article/abs/pii/S2211285520302974"
    assert url_rejection_reason(url) == "sciencedirect_abstract_landing"


def test_resolve_prefers_normalized_repository_pdf() -> None:
    paper = Paper(
        id="W1",
        title="t",
        year=2020,
        oa_url="https://www.osti.gov/biblio/1775445",
        raw={
            "unpaywall": {
                "pdf_candidates": [
                    "https://doi.org/10.1021/jacs.7b13611",
                    "https://www.osti.gov/biblio/1775445",
                ]
            }
        },
    )
    assert resolve_oa_url(paper) == "https://www.osti.gov/servlets/purl/1775445"
