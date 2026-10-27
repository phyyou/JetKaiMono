"""Download the pinned source fonts into sources_dir."""

from __future__ import annotations

import fnmatch
import hashlib
import shutil
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from .config import Config, Source


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    print(f"  downloading {url}")
    with urllib.request.urlopen(url) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out, 1 << 20)


def _extract(archive: Path, patterns: tuple[str, ...], dest_dir: Path) -> list[Path]:
    """Extract members whose basename matches any pattern, flattened into dest_dir."""
    matches = lambda name: any(fnmatch.fnmatch(PurePosixPath(name).name, p) for p in patterns)
    written = []
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if not info.is_dir() and matches(info.filename):
                    target = dest_dir / PurePosixPath(info.filename).name
                    with zf.open(info) as src, target.open("wb") as out:
                        shutil.copyfileobj(src, out)
                    written.append(target)
    else:
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                if member.isfile() and matches(member.name):
                    target = dest_dir / PurePosixPath(member.name).name
                    with tf.extractfile(member) as src, target.open("wb") as out:
                        shutil.copyfileobj(src, out)
                    written.append(target)
    return written


def fetch_source(source: Source, sources_dir: Path, force: bool = False) -> None:
    dest_dir = sources_dir / source.dest
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = dest_dir / f".{source.filename}.sha256"

    if not force and stamp.exists() and stamp.read_text().strip() == source.sha256:
        print(f"  up to date: {source.dest}/{source.filename}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_file = Path(tmp) / source.filename
        _download(source.url, tmp_file)
        digest = _sha256(tmp_file)
        if digest != source.sha256:
            raise SystemExit(
                f"sha256 mismatch for {source.url}\n  expected {source.sha256}\n  got      {digest}"
            )
        if source.extract:
            written = _extract(tmp_file, source.extract, dest_dir)
            if not written:
                raise SystemExit(f"no members of {source.filename} match {list(source.extract)}")
            print(f"  extracted {len(written)} files into {source.dest}/")
        else:
            shutil.move(tmp_file, dest_dir / source.filename)
            print(f"  saved {source.dest}/{source.filename}")
    stamp.write_text(source.sha256 + "\n")


def fetch_all(config: Config, force: bool = False) -> None:
    print(f"Fetching sources into {config.sources_dir}")
    for source in config.sources:
        fetch_source(source, config.sources_dir, force)
