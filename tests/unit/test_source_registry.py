from pathlib import Path

import pytest

from telecom_intelligence.ingestion.source_registry import load_source_registry


def test_project_source_registry_is_valid() -> None:
    registry = load_source_registry(Path("config/sources.yml"))

    assert registry["municipalities"].enabled is True
    assert registry["municipalities"].institution == "IBGE"
    assert registry["broadband"].enabled is False


def test_enabled_source_requires_resource_url(tmp_path: Path) -> None:
    source_file = tmp_path / "sources.yml"
    source_file.write_text(
        """sources:
  invalid:
    institution: TEST
    dataset: invalid
    frequency: monthly
    enabled: true
    catalog_url: null
    resource_url: null
    discovery_status: pending
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must define resource_url"):
        load_source_registry(source_file)
