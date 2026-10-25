"""Download official WFP Benin food prices and market metadata from HDX.

This module downloads only from the exact official HDX URLs recorded in
``docs/DATA.md``, verifies downloaded file sizes against expected metadata,
and computes SHA-256 and MD5 checksums for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import urllib.request


PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
RAW_DATA_DIR: Path = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class RemoteResource:
    """Metadata specification for a remote dataset resource recorded in docs/DATA.md."""

    name: str
    url: str
    filename: str
    expected_min_bytes: int
    expected_md5: str | None = None


WFP_BENIN_RESOURCES: tuple[RemoteResource, ...] = (
    RemoteResource(
        name="WFP Benin Food Prices",
        url=(
            "https://data.humdata.org/dataset/66c7d54e-0c3b-45e5-9a46-07ea6f195093/"
            "resource/7da1ea0a-56c7-450a-af2c-d477745fc856/download/wfp_food_prices_ben.csv"
        ),
        filename="wfp_food_prices_ben.csv",
        expected_min_bytes=10_000_000,
        expected_md5="a0be1e7b6de7806941d48240915284bc",
    ),
    RemoteResource(
        name="WFP Benin Markets Metadata",
        url=(
            "https://data.humdata.org/dataset/66c7d54e-0c3b-45e5-9a46-07ea6f195093/"
            "resource/030d5114-a642-4b5b-8915-019c6f1e8d4e/download/wfp_markets_ben.csv"
        ),
        filename="wfp_markets_ben.csv",
        expected_min_bytes=1_000,
        expected_md5="9cc2d01869dbf763405e40a0d6132b3a",
    ),
)


@dataclass(frozen=True)
class DownloadResult:
    """Verification summary produced after downloading a dataset resource."""

    resource: RemoteResource
    local_path: Path
    size_bytes: int
    sha256: str
    md5: str


def compute_checksums(file_path: Path, chunk_size: int = 1024 * 1024) -> tuple[str, str]:
    """Compute (SHA-256, MD5) hex digests for a local file."""
    sha256_hasher = hashlib.sha256()
    md5_hasher = hashlib.md5()
    with file_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hasher.update(chunk)
            md5_hasher.update(chunk)
    return sha256_hasher.hexdigest(), md5_hasher.hexdigest()


def download_resource(
    resource: RemoteResource,
    output_dir: Path = RAW_DATA_DIR,
    timeout_seconds: int = 120,
) -> DownloadResult:
    """Download a single resource to ``output_dir`` and verify its size and checksums."""
    output_dir.mkdir(parents=True, exist_ok=True)
    target_path = output_dir / resource.filename

    request = urllib.request.Request(
        resource.url,
        headers={"User-Agent": "BeninAgroMarket-Ingest/1.0 (Python urllib)"},
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        with target_path.open("wb") as out_file:
            while chunk := response.read(1024 * 256):
                out_file.write(chunk)

    size_bytes = target_path.stat().st_size
    if size_bytes < resource.expected_min_bytes:
        raise ValueError(
            f"Downloaded file {target_path} is unexpectedly small: "
            f"{size_bytes} bytes < {resource.expected_min_bytes} bytes."
        )

    sha256_hex, md5_hex = compute_checksums(target_path)
    return DownloadResult(
        resource=resource,
        local_path=target_path,
        size_bytes=size_bytes,
        sha256=sha256_hex,
        md5=md5_hex,
    )


def download_all_wfp(output_dir: Path = RAW_DATA_DIR) -> list[DownloadResult]:
    """Download all official WFP Benin resources recorded in ``docs/DATA.md``."""
    results: list[DownloadResult] = []
    for resource in WFP_BENIN_RESOURCES:
        result = download_resource(resource, output_dir=output_dir)
        results.append(result)
    return results


if __name__ == "__main__":
    downloaded = download_all_wfp()
    for item in downloaded:
        print(
            f"[OK] {item.resource.name}\n"
            f"     Path:    {item.local_path}\n"
            f"     Size:    {item.size_bytes:,} bytes\n"
            f"     SHA-256: {item.sha256}\n"
            f"     MD5:     {item.md5}"
        )
