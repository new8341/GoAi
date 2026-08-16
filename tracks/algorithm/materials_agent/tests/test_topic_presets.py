"""Topic preset catalog for user UI."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "configs" / "topic_presets.json"


def test_topic_presets_has_ten_competition_topics():
    data = json.loads(PRESET.read_text(encoding="utf-8"))
    topics = data["topics"]
    assert len(topics) == 10
    assert data["default_id"] == "snse-vacancy-kl"
    ids = {t["id"] for t in topics}
    assert "snse-vacancy-kl" in ids
    assert "snse-cd-vacancy" in ids
    for t in topics:
        assert t["topic"].strip()
        assert t["label_zh"].strip()
    default = next(t for t in topics if t["id"] == data["default_id"])
    assert "SnSe" in default["topic"]
    assert "vacancy" in default["topic"].lower()
