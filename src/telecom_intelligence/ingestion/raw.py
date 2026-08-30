"""Resilient and idempotent downloads into immutable RAW storage."""

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from telecom_intelligence.ingestion.manifest import IngestionManifest, ManifestRecord

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestionRequest:
    """Parameters defining one source acquisition."""

    source: str
    dataset: str
    reference_date: str
    resource_url: str


@dataclass(frozen=True)
class IngestionResult:
    """Outcome returned to orchestration code."""

    record: ManifestRecord
    downloaded: bool


class RawIngestor:
    """Download official resources without ever overwriting RAW artifacts."""

    def __init__(
        self,
        raw_root: Path,
        manifest: IngestionManifest,
        client: httpx.Client | None = None,
    ) -> None:
        self.raw_root = raw_root
        self.manifest = manifest
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(connect=30, read=300, write=30, pool=30),
            follow_redirects=True,
        )

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def _download(self, url: str, temporary_path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with self.client.stream("GET", url) as response:
            response.raise_for_status()
            with temporary_path.open("xb") as output:
                for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                    output.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
        return digest.hexdigest(), size

    def ingest(
        self, request: IngestionRequest, pipeline_run_id: str | None = None
    ) -> IngestionResult:
        """Acquire, identify, persist, and register an official source artifact."""
        run_id = pipeline_run_id or str(uuid4())
        download_timestamp = datetime.now(UTC).isoformat()
        source_file = _source_filename(request.resource_url, request.dataset)
        staging_directory = self.raw_root / ".staging"
        staging_directory.mkdir(parents=True, exist_ok=True)
        temporary_path = staging_directory / f"{run_id}.part"

        LOGGER.info(
            "Starting RAW download",
            extra={"dataset": request.dataset, "pipeline_run_id": run_id},
        )
        try:
            sha256, file_size = self._download(request.resource_url, temporary_path)
            existing = self.manifest.find(request.dataset, request.reference_date, sha256)
            if existing:
                temporary_path.unlink(missing_ok=True)
                LOGGER.info(
                    "Artifact already registered; download discarded", extra={"sha256": sha256}
                )
                return IngestionResult(record=existing, downloaded=False)

            target_directory = (
                self.raw_root
                / f"dataset={request.dataset}"
                / f"reference_date={request.reference_date}"
            )
            target_directory.mkdir(parents=True, exist_ok=True)
            target_path = target_directory / f"sha256={sha256[:16]}__{source_file}"
            if target_path.exists():
                raise FileExistsError(f"Unregistered RAW artifact already exists: {target_path}")
            os.replace(temporary_path, target_path)

            record = ManifestRecord(
                source=request.source,
                dataset=request.dataset,
                reference_date=request.reference_date,
                source_file=source_file,
                raw_path=str(target_path),
                download_timestamp=download_timestamp,
                file_size=file_size,
                sha256=sha256,
                status="downloaded",
                records_loaded=None,
                pipeline_run_id=run_id,
            )
            self.manifest.add(record)
            LOGGER.info(
                "RAW artifact persisted",
                extra={"dataset": request.dataset, "file_size": file_size, "sha256": sha256},
            )
            return IngestionResult(record=record, downloaded=True)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            LOGGER.exception(
                "RAW ingestion failed",
                extra={"dataset": request.dataset, "pipeline_run_id": run_id},
            )
            raise


def _source_filename(url: str, dataset: str) -> str:
    name = Path(unquote(urlparse(url).path)).name
    return name or f"{dataset}.json"
