"""Profile the most recent local RAW municipality directory."""

import argparse
import json
from pathlib import Path

from telecom_intelligence.quality.profiling import write_municipality_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-path", type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("reports/data_quality/municipality_directory")
    )
    return parser.parse_args()


def discover_latest_raw() -> Path:
    candidates = sorted(Path("data/raw/dataset=municipality_directory").glob("**/sha256=*"))
    if not candidates:
        raise FileNotFoundError("No municipality_directory RAW artifact found")
    return candidates[-1]


def main() -> None:
    args = parse_args()
    artifacts = write_municipality_profile(args.raw_path or discover_latest_raw(), args.output)
    print(json.dumps({key: str(value) for key, value in vars(artifacts).items()}, indent=2))


if __name__ == "__main__":
    main()
