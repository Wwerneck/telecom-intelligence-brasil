"""Profile the latest official SIDRA population RAW artifact."""

import json
from pathlib import Path

from telecom_intelligence.quality.population_profiling import write_population_profile


def latest(pattern: str) -> Path:
    candidates = sorted(Path().glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No artifact found for {pattern}")
    return candidates[-1]


def main() -> None:
    profile = write_population_profile(
        latest("data/raw/dataset=municipality_population/reference_date=*/sha256=*"),
        latest("data/gold/dim_municipality/*.parquet"),
        Path("reports/data_quality/municipality_population/profile_2025.json"),
    )
    print(json.dumps(vars(profile), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
