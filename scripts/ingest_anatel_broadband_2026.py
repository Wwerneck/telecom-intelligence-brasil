"""Selectively ingest the 2026 broadband member from ANATEL's official archive."""

import json
from pathlib import Path

from telecom_intelligence.ingestion.manifest import IngestionManifest
from telecom_intelligence.ingestion.remote_zip import ingest_remote_zip_member
from telecom_intelligence.ingestion.source_registry import load_source_registry


def main() -> None:
    source = load_source_registry(Path("config/sources.yml"))["broadband"]
    if not source.resource_url or not source.archive_member:
        raise RuntimeError("Broadband archive configuration is incomplete")
    result = ingest_remote_zip_member(
        source=source.institution,
        dataset=source.dataset,
        reference_date="2026",
        archive_url=source.resource_url,
        member_name=source.archive_member,
        raw_root=Path("data/raw"),
        manifest=IngestionManifest(Path("data/ingestion_manifest.db")),
    )
    print(json.dumps(vars(result.record) | {"downloaded": result.downloaded}, indent=2))


if __name__ == "__main__":
    main()
