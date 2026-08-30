"""Ingest verified annual municipal population estimates from SIDRA/IBGE."""

import argparse
import json
import logging
from pathlib import Path

from telecom_intelligence.ingestion.manifest import IngestionManifest
from telecom_intelligence.ingestion.raw import IngestionRequest, RawIngestor
from telecom_intelligence.ingestion.source_registry import load_source_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2025")
    parser.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/ingestion_manifest.db"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    source = load_source_registry(Path("config/sources.yml"))["population"]
    if not source.enabled or not source.resource_url:
        raise RuntimeError("The population source is not ready for ingestion")
    if str(source.period) != args.period:
        raise ValueError(
            f"Configured SIDRA resource is for {source.period}; received period {args.period}"
        )

    result = RawIngestor(args.raw_root, IngestionManifest(args.manifest)).ingest(
        IngestionRequest(
            source=source.institution,
            dataset=source.dataset,
            reference_date=args.period,
            resource_url=source.resource_url,
        )
    )
    print(
        json.dumps(
            {
                "downloaded": result.downloaded,
                "dataset": result.record.dataset,
                "reference_date": result.record.reference_date,
                "raw_path": result.record.raw_path,
                "file_size": result.record.file_size,
                "sha256": result.record.sha256,
                "status": result.record.status,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
