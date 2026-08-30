"""Build validated Silver municipalities and the corresponding quarantine artifact."""

import json
from pathlib import Path

from telecom_intelligence.transformation.silver import transform_municipality_to_silver


def latest_bronze() -> Path:
    candidates = sorted(Path("data/bronze/dataset=municipality_directory").glob("**/*.parquet"))
    if not candidates:
        raise FileNotFoundError("No municipality Bronze artifact found")
    return candidates[-1]


def main() -> None:
    result = transform_municipality_to_silver(
        latest_bronze(),
        Path("config/schemas/municipality_directory_silver.yml"),
        Path("data/silver"),
        Path("data/quarantine"),
    )
    print(json.dumps({key: str(value) for key, value in vars(result).items()}, indent=2))


if __name__ == "__main__":
    main()
