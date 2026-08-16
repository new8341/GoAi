"""Dual MP+OQMD validation combine logic."""

from materials_agent.tools.materials_db import ValidationResult, _combine_mp_oqmd


def test_combine_both_pass():
    mp = ValidationResult("SnSe", "SnSe", "pass", "materials_project", 0.0, True, "mp-1")
    oq = ValidationResult("SnSe", "SnSe", "pass", "oqmd", 0.0, True, "oq")
    r = _combine_mp_oqmd(mp, oq)
    assert r.provider == "mp_oqmd"
    assert r.verdict == "pass"


def test_combine_one_pass():
    mp = ValidationResult("SnSe", "SnSe", "pass", "materials_project", 0.0, True, "mp-1")
    oq = ValidationResult("SnSe", "SnSe", "fail", "oqmd", 0.2, False, "oq")
    r = _combine_mp_oqmd(mp, oq)
    assert r.verdict == "pass"
