from materials_agent.config import AppConfig
from materials_agent.tools.materials_db import validate_motif


def test_production_materials_db_does_not_silently_fallback(tmp_path) -> None:
    cfg = AppConfig(
        topic="SnSe",
        materials_db={
            "provider": "materials_project",
            "mp_api_key": "",
            "allow_offline_fallback": False,
            "cache_path": str(tmp_path / "cache.json"),
        },
        route_a={"materials_db": "materials_project"},
    )

    result = validate_motif("SnSe", cfg)

    assert result.provider == "materials_project"
    assert result.verdict == "error"
