import csv
import io
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DOWNLOAD_TIMEOUT_SECONDS = 120


def read_dataset_rows(location: str) -> Iterator[dict[str, str]]:
    """Yields rows of an ANS open-data CSV (or of every CSV inside a zip), from a path or URL."""
    with materialize_location(location) as path:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for member in sorted(archive.namelist()):
                    if member.lower().endswith(".csv"):
                        with archive.open(member) as raw:
                            yield from read_csv_rows(raw)
        else:
            with path.open("rb") as raw:
                yield from read_csv_rows(raw)


def read_csv_rows(raw_binary) -> Iterator[dict[str, str]]:
    text = io.TextIOWrapper(raw_binary, encoding="utf-8-sig", errors="replace", newline="")
    for row in csv.DictReader(text, delimiter=";"):
        yield {key.strip(): (value or "").strip() for key, value in row.items() if key}


@contextmanager
def materialize_location(location: str) -> Iterator[Path]:
    if not location.startswith(("http://", "https://")):
        yield Path(location)
        return
    suffix = Path(location).suffix or ".csv"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
        with urllib.request.urlopen(location, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            shutil.copyfileobj(response, temporary)
        downloaded = Path(temporary.name)
    try:
        yield downloaded
    finally:
        downloaded.unlink(missing_ok=True)
