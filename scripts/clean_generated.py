"""Remove only known generated development artifacts."""

from pathlib import Path
from shutil import rmtree

GENERATED_DIRECTORIES = (".pytest_cache", ".ruff_cache", "htmlcov", "dbt/target", "dbt/logs")


def main() -> None:
    """Delete allow-listed generated directories below the repository root."""
    repository_root = Path(__file__).resolve().parents[1]
    for relative_path in GENERATED_DIRECTORIES:
        target = (repository_root / relative_path).resolve()
        if repository_root not in target.parents:
            raise RuntimeError(f"Refusing to clean path outside repository: {target}")
        if target.exists():
            rmtree(target)


if __name__ == "__main__":
    main()
