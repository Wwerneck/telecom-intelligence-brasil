"""Build the Gold fixed-broadband fact from validated Silver partitions."""

import json
from pathlib import Path

from telecom_intelligence.transformation.fact_broadband import build_broadband_fact


def latest(paths: list[Path]) -> Path:
    if not paths:
        raise FileNotFoundError("Required dimensional artifact not found")
    return sorted(paths)[-1]


def main() -> None:
    silver = sorted(
        Path("data/silver/dataset=fixed_broadband_accesses").glob("year=*/month=*/*.parquet")
    )
    result = build_broadband_fact(
        silver,
        latest(list(Path("data/gold/dim_municipality").glob("*.parquet"))),
        Path("data/gold"),
    )
    print(json.dumps(vars(result), default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
