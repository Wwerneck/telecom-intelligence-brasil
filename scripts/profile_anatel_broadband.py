"""Profile the latest official ANATEL fixed-broadband RAW artifact."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from telecom_intelligence.quality.broadband_profiling import write_broadband_profile


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=100_000)
    args = parser.parse_args()
    candidates = sorted(Path("data/raw/dataset=fixed_broadband_accesses").glob("**/*.csv"))
    if not candidates:
        raise FileNotFoundError("No fixed-broadband RAW artifact found")
    profile = write_broadband_profile(
        candidates[-1],
        Path("reports/data_quality/fixed_broadband_accesses/profile_2026.json"),
        args.chunk_size,
    )
    print(json.dumps(asdict(profile), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
