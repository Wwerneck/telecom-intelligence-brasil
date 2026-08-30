"""Build audited reference marts from the Gold fixed-broadband fact."""

import json
from pathlib import Path

import pyarrow.parquet as pq

from telecom_intelligence.analytics.broadband_marts import build_broadband_marts


def populated_municipality_dimension(paths: list[Path]) -> Path:
    """Select the version whose population columns have complete statistics."""
    for path in sorted(paths, reverse=True):
        metadata = pq.read_metadata(path)
        population_index = metadata.schema.names.index("population")
        nulls = sum(
            metadata.row_group(group).column(population_index).statistics.null_count
            for group in range(metadata.num_row_groups)
        )
        if nulls == 0:
            return path
    raise FileNotFoundError("No municipality dimension with complete population found")


def main() -> None:
    facts = sorted(Path("data/gold/fact_broadband_accesses").glob("year=*/month=*/*.parquet"))
    result = build_broadband_marts(
        facts,
        populated_municipality_dimension(
            list(Path("data/gold/dim_municipality").glob("*.parquet"))
        ),
        Path("data/gold/marts"),
    )
    print(json.dumps(vars(result), default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
