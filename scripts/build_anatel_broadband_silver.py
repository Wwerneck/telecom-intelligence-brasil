"""Build the validated monthly ANATEL fixed-broadband Silver layer."""

import json
from pathlib import Path

from telecom_intelligence.transformation.broadband_silver import build_broadband_silver


def latest(paths: list[Path]) -> Path:
    if not paths:
        raise FileNotFoundError("Required upstream artifact not found")
    return sorted(paths)[-1]


def main() -> None:
    bronze = sorted(
        Path("data/bronze/dataset=fixed_broadband_accesses").glob("year=*/month=*/*.parquet")
    )
    result = build_broadband_silver(
        bronze,
        latest(list(Path("data/gold/dim_municipality").glob("*.parquet"))),
        Path("config/schemas/fixed_broadband_accesses_silver.yml"),
        Path("data/silver"),
        Path("data/quarantine"),
    )
    print(json.dumps(vars(result), default=str, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
