import io
import zipfile
from pathlib import Path

import httpx

from telecom_intelligence.ingestion.manifest import IngestionManifest
from telecom_intelligence.ingestion.remote_zip import (
    RemoteZipExtractor,
    ingest_remote_zip_member,
)


def archive_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("official.csv", "id,value\n1,10\n")
        archive.writestr("ignored.csv", "ignore\n")
    return buffer.getvalue()


def ranged_client(content: bytes) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-length": str(len(content))})
        byte_range = request.headers.get("range")
        assert byte_range is not None
        start_text, end_text = byte_range.removeprefix("bytes=").split("-")
        start, end = int(start_text), min(int(end_text), len(content) - 1)
        return httpx.Response(
            206,
            content=content[start : end + 1],
            headers={"content-range": f"bytes {start}-{end}/{len(content)}"},
        )

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_remote_zip_discovers_and_extracts_only_selected_member(tmp_path: Path) -> None:
    content = archive_bytes()
    extractor = RemoteZipExtractor(ranged_client(content))

    length, members = extractor.discover("https://official.example/data.zip")
    selected = next(member for member in members if member.name == "official.csv")
    target = tmp_path / "official.csv"
    _, size = extractor.extract("https://official.example/data.zip", selected, target)

    assert length == len(content)
    assert size == len(b"id,value\n1,10\n")
    assert target.read_bytes() == b"id,value\n1,10\n"


def test_remote_zip_ingestion_registers_archive_lineage(tmp_path: Path) -> None:
    extractor = RemoteZipExtractor(ranged_client(archive_bytes()))
    manifest = IngestionManifest(tmp_path / "manifest.db")

    result = ingest_remote_zip_member(
        "ANATEL",
        "fixed_broadband_accesses",
        "2026",
        "https://official.example/data.zip",
        "official.csv",
        tmp_path / "raw",
        manifest,
        extractor,
    )

    assert result.downloaded is True
    assert result.record.archive_member == "official.csv"
    assert result.record.compressed_size is not None
    assert manifest.count() == 1

    second = ingest_remote_zip_member(
        "ANATEL",
        "fixed_broadband_accesses",
        "2026",
        "https://official.example/data.zip",
        "official.csv",
        tmp_path / "raw",
        manifest,
        extractor,
    )
    assert second.downloaded is False
    assert manifest.count() == 1
