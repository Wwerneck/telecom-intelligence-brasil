"""SQLite-backed audit manifest for immutable RAW ingestion."""

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class ManifestRecord:
    """One immutable source artifact observed by the ingestion pipeline."""

    source: str
    dataset: str
    reference_date: str
    source_file: str
    raw_path: str
    download_timestamp: str
    file_size: int
    sha256: str
    status: str
    records_loaded: int | None
    pipeline_run_id: str
    source_url: str | None = None
    archive_member: str | None = None
    archive_crc32: str | None = None
    compressed_size: int | None = None


class IngestionManifest:
    """Persist ingestion metadata and enforce dataset/reference/hash uniqueness."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_manifest (
                    manifest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    dataset TEXT NOT NULL,
                    reference_date TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    raw_path TEXT NOT NULL,
                    download_timestamp TEXT NOT NULL,
                    file_size INTEGER NOT NULL CHECK (file_size >= 0),
                    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
                    status TEXT NOT NULL,
                    records_loaded INTEGER,
                    pipeline_run_id TEXT NOT NULL,
                    source_url TEXT,
                    archive_member TEXT,
                    archive_crc32 TEXT,
                    compressed_size INTEGER,
                    created_at TEXT NOT NULL,
                    UNIQUE (dataset, reference_date, sha256)
                )
                """
            )
            existing_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(ingestion_manifest)")
            }
            migrations = {
                "source_url": "TEXT",
                "archive_member": "TEXT",
                "archive_crc32": "TEXT",
                "compressed_size": "INTEGER",
            }
            for name, data_type in migrations.items():
                if name not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE ingestion_manifest ADD COLUMN {name} {data_type}"
                    )

    def find(self, dataset: str, reference_date: str, sha256: str) -> ManifestRecord | None:
        """Return a previously registered artifact with the same business identity."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT source, dataset, reference_date, source_file, raw_path,
                       download_timestamp, file_size, sha256, status,
                       records_loaded, pipeline_run_id, source_url, archive_member,
                       archive_crc32, compressed_size
                FROM ingestion_manifest
                WHERE dataset = ? AND reference_date = ? AND sha256 = ?
                """,
                (dataset, reference_date, sha256),
            ).fetchone()
        return ManifestRecord(**dict(row)) if row else None

    def add(self, record: ManifestRecord) -> None:
        """Register a newly persisted RAW artifact."""
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO ingestion_manifest (
                    source, dataset, reference_date, source_file, raw_path,
                    download_timestamp, file_size, sha256, status,
                    records_loaded, pipeline_run_id, source_url, archive_member,
                    archive_crc32, compressed_size, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.source,
                    record.dataset,
                    record.reference_date,
                    record.source_file,
                    record.raw_path,
                    record.download_timestamp,
                    record.file_size,
                    record.sha256,
                    record.status,
                    record.records_loaded,
                    record.pipeline_run_id,
                    record.source_url,
                    record.archive_member,
                    record.archive_crc32,
                    record.compressed_size,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def find_archive_member(
        self,
        dataset: str,
        reference_date: str,
        source_url: str,
        archive_member: str,
        archive_crc32: str,
        compressed_size: int,
    ) -> ManifestRecord | None:
        """Find a member whose immutable ZIP identity was already ingested."""
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT source, dataset, reference_date, source_file, raw_path,
                       download_timestamp, file_size, sha256, status,
                       records_loaded, pipeline_run_id, source_url, archive_member,
                       archive_crc32, compressed_size
                FROM ingestion_manifest
                WHERE dataset = ? AND reference_date = ? AND source_url = ?
                  AND archive_member = ? AND archive_crc32 = ? AND compressed_size = ?
                """,
                (
                    dataset,
                    reference_date,
                    source_url,
                    archive_member,
                    archive_crc32,
                    compressed_size,
                ),
            ).fetchone()
        return ManifestRecord(**dict(row)) if row else None

    def count(self) -> int:
        """Return the number of registered artifacts."""
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM ingestion_manifest").fetchone()
        return int(row["total"])
