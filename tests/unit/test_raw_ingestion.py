import hashlib
from pathlib import Path

import httpx

from telecom_intelligence.ingestion.manifest import IngestionManifest
from telecom_intelligence.ingestion.raw import IngestionRequest, RawIngestor


def test_raw_ingestion_is_immutable_and_idempotent(tmp_path: Path) -> None:
    payload = b'[{"id": 5200050, "nome": "Abadia de Goias"}]'

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://official.example/municipios"
        return httpx.Response(200, content=payload, headers={"content-type": "application/json"})

    manifest = IngestionManifest(tmp_path / "manifest.db")
    ingestor = RawIngestor(
        tmp_path / "raw",
        manifest,
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    request = IngestionRequest(
        source="IBGE",
        dataset="municipality_directory",
        reference_date="2026-08-28",
        resource_url="https://official.example/municipios",
    )

    first = ingestor.ingest(request, pipeline_run_id="run-1")
    second = ingestor.ingest(request, pipeline_run_id="run-2")

    assert first.downloaded is True
    assert second.downloaded is False
    assert manifest.count() == 1
    assert Path(first.record.raw_path).read_bytes() == payload
    assert first.record.sha256 == hashlib.sha256(payload).hexdigest()
    assert not list((tmp_path / "raw" / ".staging").glob("*.part"))


def test_failed_download_does_not_leave_partial_file(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, request=request)

    ingestor = RawIngestor(
        tmp_path / "raw",
        IngestionManifest(tmp_path / "manifest.db"),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    request = IngestionRequest("IBGE", "missing", "2026-08-28", "https://example.test/x")

    try:
        ingestor.ingest(request, pipeline_run_id="failed-run")
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError("Expected HTTPStatusError")

    assert not list((tmp_path / "raw" / ".staging").glob("*.part"))
