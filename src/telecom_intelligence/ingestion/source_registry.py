"""Load and validate the centralized registry of official sources."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SourceDefinition:
    """Configuration required to discover or ingest one official dataset."""

    name: str
    institution: str
    dataset: str
    frequency: str
    enabled: bool
    catalog_url: str | None
    resource_url: str | None
    discovery_status: str
    table: int | None = None
    variable: int | None = None
    period: int | None = None
    archive_member: str | None = None
    content_length: int | None = None

    def validate(self) -> None:
        """Reject configurations that could enable an unverified resource."""
        if self.enabled and not self.resource_url:
            raise ValueError(f"Enabled source {self.name!r} must define resource_url")
        if self.resource_url and not self.resource_url.startswith("https://"):
            raise ValueError(f"Source {self.name!r} must use an HTTPS resource URL")


def load_source_registry(path: Path) -> dict[str, SourceDefinition]:
    """Read source definitions from YAML and enforce minimum discovery contracts."""
    document: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw_sources = document.get("sources")
    if not isinstance(raw_sources, dict) or not raw_sources:
        raise ValueError("Source registry must contain a non-empty 'sources' mapping")

    registry: dict[str, SourceDefinition] = {}
    for name, values in raw_sources.items():
        source = SourceDefinition(name=name, **values)
        source.validate()
        registry[name] = source
    return registry
