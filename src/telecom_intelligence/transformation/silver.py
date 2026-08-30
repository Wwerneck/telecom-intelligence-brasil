"""Validated municipality Silver transformation with explicit quarantine."""

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from telecom_intelligence.transformation.text import matching_key, normalize_display_text


@dataclass(frozen=True)
class SilverResult:
    """Counts and artifacts produced by one Bronze-to-Silver execution."""

    silver_path: Path
    quarantine_path: Path
    records_input: int
    records_output: int
    records_rejected: int
    created: bool


def load_silver_contract(path: Path) -> dict[str, Any]:
    """Read the versioned Silver data contract."""
    contract = yaml.safe_load(path.read_text(encoding="utf-8"))
    if contract.get("layer") != "silver" or not contract.get("primary_key"):
        raise ValueError("Invalid Silver schema contract")
    return contract


def clean_municipality_text(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean display fields and add a separate matching key."""
    cleaned = frame.copy()
    display_columns = [column for column in cleaned if column.endswith("_name")]
    for column in display_columns:
        cleaned[column] = cleaned[column].map(
            lambda value: normalize_display_text(value) if pd.notna(value) else value
        )
    cleaned["municipality_key"] = cleaned["municipality_name"].map(
        lambda value: matching_key(value) if pd.notna(value) else pd.NA
    )
    return cleaned


def classify_municipality_rejections(frame: pd.DataFrame, contract: dict[str, Any]) -> pd.Series:
    """Return a pipe-separated reason for each invalid record, or an empty string."""
    reasons: list[list[str]] = [[] for _ in range(len(frame))]

    def add(mask: pd.Series, reason: str) -> None:
        for position in mask.fillna(True).to_numpy().nonzero()[0]:
            reasons[position].append(reason)

    code_text = frame["ibge_code"].astype("string")
    add(~code_text.str.fullmatch(r"\d{7}"), "invalid_ibge_code")
    add(frame["municipality_name"].isna() | frame["municipality_name"].eq(""), "missing_name")
    add(frame["municipality_key"].isna() | frame["municipality_key"].eq(""), "invalid_name_key")
    add(
        ~frame["state_code"].isin(contract["accepted_values"]["state_code"]),
        "invalid_state_code",
    )
    add(
        ~frame["region_name"].isin(contract["accepted_values"]["region_name"]),
        "invalid_region",
    )
    add(frame.duplicated(subset=[contract["primary_key"]], keep=False), "duplicate_key")
    return pd.Series(("|".join(item) for item in reasons), index=frame.index, dtype="string")


def transform_frame(
    bronze: pd.DataFrame,
    contract: dict[str, Any],
    rejection_timestamp: datetime | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply controlled cleaning and split valid and rejected records."""
    missing_columns = set(contract["required_columns"]).difference(
        set(bronze.columns) | {"municipality_key"}
    )
    if missing_columns:
        raise ValueError(f"Critical schema drift: missing {sorted(missing_columns)}")

    cleaned = clean_municipality_text(bronze)
    rejection_reason = classify_municipality_rejections(cleaned, contract)
    rejected = cleaned.loc[rejection_reason.ne("")].copy()
    rejected["rejection_reason"] = rejection_reason[rejection_reason.ne("")]
    rejected["source"] = rejected["_source_file"]
    rejected["pipeline_run"] = rejected["_pipeline_run_id"]
    rejected["rejection_timestamp"] = (rejection_timestamp or datetime.now(UTC)).isoformat()
    valid = cleaned.loc[rejection_reason.eq("")].copy()
    valid["_silver_timestamp"] = (rejection_timestamp or datetime.now(UTC)).isoformat()
    valid["_silver_schema_version"] = int(contract["version"])
    return valid.reset_index(drop=True), rejected.reset_index(drop=True)


def _write_parquet_once(frame: pd.DataFrame, target: Path, metadata: dict[bytes, bytes]) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    temporary = target.parent / f".{target.name}.part"
    table = pa.Table.from_pandas(frame, preserve_index=False)
    try:
        pq.write_table(
            table.replace_schema_metadata({**(table.schema.metadata or {}), **metadata}),
            temporary,
            compression="zstd",
        )
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def transform_municipality_to_silver(
    bronze_path: Path,
    contract_path: Path,
    silver_root: Path,
    quarantine_root: Path,
) -> SilverResult:
    """Read Bronze, validate every row, and persist Silver plus quarantine."""
    bronze = pd.read_parquet(bronze_path)
    contract = load_silver_contract(contract_path)
    valid, rejected = transform_frame(bronze, contract)
    sha256 = str(bronze["_sha256"].iloc[0])
    reference_date = str(bronze["_reference_date"].iloc[0])
    dataset = str(contract["dataset"])
    filename = f"sha256={sha256[:16]}.parquet"
    silver_path = silver_root / f"dataset={dataset}" / f"reference_date={reference_date}" / filename
    quarantine_path = (
        quarantine_root
        / "invalid_municipality"
        / f"dataset={dataset}"
        / f"reference_date={reference_date}"
        / filename
    )
    metadata = {b"source_sha256": sha256.encode(), b"reference_date": reference_date.encode()}
    created = _write_parquet_once(valid, silver_path, {**metadata, b"layer": b"silver"})
    _write_parquet_once(rejected, quarantine_path, {**metadata, b"layer": b"quarantine"})
    return SilverResult(
        silver_path=silver_path,
        quarantine_path=quarantine_path,
        records_input=len(bronze),
        records_output=len(valid),
        records_rejected=len(rejected),
        created=created,
    )
