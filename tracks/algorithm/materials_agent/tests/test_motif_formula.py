from materials_agent.tools.materials_db import extract_chemical_formula


def test_extract_snse_from_prose() -> None:
    assert extract_chemical_formula("SnSe vacancy engineering") == "SnSe"


def test_reject_lead_chalcogenides_prose() -> None:
    assert extract_chemical_formula("Lead chalcogenides (for comparison)") is None


def test_extract_pbte() -> None:
    assert extract_chemical_formula("PbTe") == "PbTe"
