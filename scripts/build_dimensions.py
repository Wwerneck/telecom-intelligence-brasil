"""Build supported dimensional models from the latest municipality Silver artifact."""

import json
from pathlib import Path

from telecom_intelligence.transformation.dimensional import build_dimensions


def latest_silver() -> Path:
    candidates = sorted(Path("data/silver/dataset=municipality_directory").glob("**/*.parquet"))
    if not candidates:
        raise FileNotFoundError("No municipality Silver artifact found")
    return candidates[-1]


def latest_population_silver() -> Path | None:
    candidates = sorted(Path("data/silver/dataset=municipality_population").glob("**/*.parquet"))
    return candidates[-1] if candidates else None


def main() -> None:
    result = build_dimensions(
        latest_silver(), Path("data/gold"), population_silver_path=latest_population_silver()
    )
    print(json.dumps({key: str(value) for key, value in vars(result).items()}, indent=2))


if __name__ == "__main__":
    main()
