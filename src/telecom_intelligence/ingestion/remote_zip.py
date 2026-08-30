"""Selective HTTP Range extraction of members from large remote ZIP archives."""

import hashlib
import os
import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

from telecom_intelligence.ingestion.manifest import IngestionManifest, ManifestRecord
from telecom_intelligence.ingestion.raw import IngestionResult


@dataclass(frozen=True)
class ZipMember:
    """Metadata read from one ZIP central-directory entry."""

    name: str
    compression_method: int
    crc32: int
    compressed_size: int
    uncompressed_size: int
    local_header_offset: int


def parse_central_directory(content: bytes) -> list[ZipMember]:
    """Parse standard, non-ZIP64 central-directory entries."""
    members: list[ZipMember] = []
    offset = 0
    while offset < len(content):
        if content[offset : offset + 4] != b"PK\x01\x02":
            raise ValueError(f"Invalid central-directory signature at byte {offset}")
        values = struct.unpack_from("<4s6H3L5H2L", content, offset)
        name_length, extra_length, comment_length = values[10:13]
        name_start = offset + 46
        name = content[name_start : name_start + name_length].decode("utf-8")
        members.append(
            ZipMember(
                name=name,
                compression_method=values[4],
                crc32=values[7],
                compressed_size=values[8],
                uncompressed_size=values[9],
                local_header_offset=values[16],
            )
        )
        offset += 46 + name_length + extra_length + comment_length
    return members


class RemoteZipExtractor:
    """Discover and extract one remote ZIP member without downloading the archive."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=300, follow_redirects=True)

    def _range(self, url: str, start: int, end: int) -> httpx.Response:
        response = self.client.get(url, headers={"Range": f"bytes={start}-{end}"})
        response.raise_for_status()
        if response.status_code != 206:
            raise ValueError("Server did not honor HTTP Range request")
        return response

    def discover(self, url: str) -> tuple[int, list[ZipMember]]:
        """Read the EOCD and central directory using small byte ranges."""
        head = self.client.head(url)
        head.raise_for_status()
        content_length = int(head.headers["content-length"])
        tail_size = min(content_length, 131_072)
        tail = self._range(url, content_length - tail_size, content_length - 1).content
        eocd_offset = tail.rfind(b"PK\x05\x06")
        if eocd_offset < 0:
            raise ValueError("ZIP end-of-central-directory record not found")
        eocd = struct.unpack_from("<4s4H2LH", tail, eocd_offset)
        central_size, central_offset = eocd[5], eocd[6]
        central = self._range(url, central_offset, central_offset + central_size - 1).content
        return content_length, parse_central_directory(central)

    def extract(self, url: str, member: ZipMember, target: Path) -> tuple[str, int]:
        """Stream, decompress, and validate one member into a new target file."""
        header = self._range(
            url, member.local_header_offset, member.local_header_offset + 65_535
        ).content
        if header[:4] != b"PK\x03\x04":
            raise ValueError("Invalid ZIP local-file header")
        values = struct.unpack_from("<4s5H3L2H", header, 0)
        name_length, extra_length = values[9], values[10]
        data_start = member.local_header_offset + 30 + name_length + extra_length
        data_end = data_start + member.compressed_size - 1
        decompressor = (
            zlib.decompressobj(-zlib.MAX_WBITS) if member.compression_method == 8 else None
        )
        if member.compression_method not in {0, 8}:
            raise ValueError(f"Unsupported ZIP compression method: {member.compression_method}")
        digest = hashlib.sha256()
        crc32 = 0
        size = 0
        target.parent.mkdir(parents=True, exist_ok=True)
        with self.client.stream(
            "GET", url, headers={"Range": f"bytes={data_start}-{data_end}"}
        ) as response:
            response.raise_for_status()
            if response.status_code != 206:
                raise ValueError("Server did not honor member Range request")
            with target.open("xb") as output:
                for compressed_chunk in response.iter_bytes(1024 * 1024):
                    chunk = (
                        decompressor.decompress(compressed_chunk)
                        if decompressor is not None
                        else compressed_chunk
                    )
                    if chunk:
                        output.write(chunk)
                        digest.update(chunk)
                        crc32 = zlib.crc32(chunk, crc32)
                        size += len(chunk)
                if decompressor is not None:
                    chunk = decompressor.flush()
                    output.write(chunk)
                    digest.update(chunk)
                    crc32 = zlib.crc32(chunk, crc32)
                    size += len(chunk)
        if size != member.uncompressed_size or crc32 != member.crc32:
            target.unlink(missing_ok=True)
            raise ValueError("Extracted ZIP member failed size or CRC-32 validation")
        return digest.hexdigest(), size


def ingest_remote_zip_member(
    source: str,
    dataset: str,
    reference_date: str,
    archive_url: str,
    member_name: str,
    raw_root: Path,
    manifest: IngestionManifest,
    extractor: RemoteZipExtractor | None = None,
) -> IngestionResult:
    """Extract an official ZIP member into immutable RAW and register its lineage."""
    extractor = extractor or RemoteZipExtractor()
    _, members = extractor.discover(archive_url)
    member = next((item for item in members if item.name == member_name), None)
    if member is None:
        raise FileNotFoundError(f"ZIP member not found: {member_name}")
    archive_crc32 = f"{member.crc32:08x}"
    existing_member = manifest.find_archive_member(
        dataset,
        reference_date,
        archive_url,
        member.name,
        archive_crc32,
        member.compressed_size,
    )
    if existing_member:
        return IngestionResult(existing_member, downloaded=False)
    run_id = str(uuid4())
    staging = raw_root / ".staging"
    staging.mkdir(parents=True, exist_ok=True)
    temporary = staging / f"{run_id}.part"
    try:
        sha256, size = extractor.extract(archive_url, member, temporary)
        existing = manifest.find(dataset, reference_date, sha256)
        if existing:
            temporary.unlink(missing_ok=True)
            return IngestionResult(existing, downloaded=False)
        directory = raw_root / f"dataset={dataset}" / f"reference_date={reference_date}"
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / f"sha256={sha256[:16]}__{member.name}"
        if target.exists():
            raise FileExistsError(target)
        os.replace(temporary, target)
        record = ManifestRecord(
            source=source,
            dataset=dataset,
            reference_date=reference_date,
            source_file=member.name,
            raw_path=str(target),
            download_timestamp=datetime.now(UTC).isoformat(),
            file_size=size,
            sha256=sha256,
            status="downloaded",
            records_loaded=None,
            pipeline_run_id=run_id,
            source_url=archive_url,
            archive_member=member.name,
            archive_crc32=archive_crc32,
            compressed_size=member.compressed_size,
        )
        manifest.add(record)
        return IngestionResult(record, downloaded=True)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
