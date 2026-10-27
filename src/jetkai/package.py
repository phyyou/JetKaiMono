"""Zip built fonts per family for a release, with checksums and release notes."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from .config import Config
from .naming import postscript_name

EXTRA_FILES = ("OFL.txt", "README.md")


def _source_releases(config: Config) -> list[str]:
    """'repo tag' for each pinned GitHub release, in config order."""
    seen = []
    for source in config.sources:
        parts = source.url.split("/")
        if "download" in parts:
            i = parts.index("download")
            entry = f"{parts[i - 2]} {parts[i + 1]}"  # .../{repo}/releases/download/{tag}/...
            if entry not in seen:
                seen.append(entry)
    return seen


def package(config: Config, variants: list[str], styles: list[str]) -> list[Path]:
    ttf_dir = config.output_dir / "ttf"
    dist = config.output_dir / "dist"
    dist.mkdir(parents=True, exist_ok=True)

    archives = []
    for key in variants:
        family = config.variants[key].family
        fonts = [ttf_dir / f"{postscript_name(family, config.styles[s])}.ttf" for s in styles]
        missing = [f.name for f in fonts if not f.exists()]
        if missing:
            raise SystemExit(f"missing built fonts {missing}; run `jetkai build` first")

        archive = dist / f"{family.replace(' ', '')}-v{config.version}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for font in fonts:
                zf.write(font, f"{archive.stem}/{font.name}")
            for name in EXTRA_FILES:
                zf.write(config.root / name, f"{archive.stem}/{name}")
        print(f"  {archive.name}: {len(fonts)} fonts, {archive.stat().st_size / 1e6:.0f} MB")
        archives.append(archive)

    sums = [f"{hashlib.sha256(a.read_bytes()).hexdigest()}  {a.name}" for a in archives]
    (dist / "SHA256SUMS").write_text("\n".join(sums) + "\n")

    notes = [
        "## Downloads",
        "",
        "- `JetKaiMono-*.zip`: with JetBrains Mono ligatures",
        "- `JetKaiMonoNL-*.zip`: without ligatures",
        "",
        "Each archive holds the TTFs for every style plus the license.",
        "",
        "## Built from",
        "",
        *[f"- {entry}" for entry in _source_releases(config)],
        "",
    ]
    # Kept outside dist/ so it is not uploaded as an asset.
    (config.output_dir / "release-notes.md").write_text("\n".join(notes))
    return archives
