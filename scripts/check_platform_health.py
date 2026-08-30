"""Run operational checks and persist their latest machine-readable result."""

import json
from pathlib import Path

from telecom_intelligence.quality.platform_health import check_platform_health


def main() -> None:
    health = check_platform_health(Path())
    output = Path("reports/observability/latest_health.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(health.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(health.as_dict(), ensure_ascii=False, indent=2))
    if health.status != "healthy":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
