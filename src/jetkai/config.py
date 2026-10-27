"""Typed view of config.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Source:
    dest: str
    url: str
    sha256: str
    extract: tuple[str, ...] = ()  # archive member globs; empty means the URL is the file itself

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


@dataclass(frozen=True)
class Variant:
    key: str
    family: str
    base: str  # path template under sources_dir with {style}


@dataclass(frozen=True)
class Style:
    key: str  # e.g. "LightItalic"
    cjk_weight: str  # WenKai weight, e.g. "Light"

    @property
    def italic(self) -> bool:
        return self.key.endswith("Italic")

    @property
    def weight(self) -> str:
        return self.key.removesuffix("Italic") or "Regular"


@dataclass(frozen=True)
class Layer:
    name: str
    path: str  # path template under sources_dir with {weight}


@dataclass(frozen=True)
class Metrics:
    cell_width: int
    cjk_scale: float
    cjk_center_y: float


@dataclass(frozen=True)
class Config:
    root: Path
    version: str
    author: str
    url: str
    description: str
    sources_dir: Path
    sources: tuple[Source, ...]
    variants: dict[str, Variant]
    styles: dict[str, Style]
    layers: tuple[Layer, ...]
    cjk_ranges: tuple[tuple[int, int], ...]
    metrics: Metrics
    output_dir: Path
    jobs: int

    def base_path(self, variant: Variant, style: Style) -> Path:
        return self.sources_dir / variant.base.format(style=style.key)

    def layer_path(self, layer: Layer, style: Style) -> Path:
        return self.sources_dir / layer.path.format(weight=style.cjk_weight)

    def in_cjk_ranges(self, codepoint: int) -> bool:
        return any(lo <= codepoint <= hi for lo, hi in self.cjk_ranges)


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = path.resolve().parent
    font = raw["font"]
    return Config(
        root=root,
        version=str(font["version"]),
        author=font["author"],
        url=font["url"],
        description=font["description"],
        sources_dir=root / raw["sources_dir"],
        sources=tuple(
            Source(s["dest"], s["url"], s["sha256"], tuple(s.get("extract", ())))
            for s in raw["sources"]
        ),
        variants={k: Variant(k, v["family"], v["base"]) for k, v in raw["variants"].items()},
        styles={k: Style(k, v) for k, v in raw["styles"].items()},
        layers=tuple(Layer(l["name"], l["path"]) for l in raw["cjk_layers"]),
        cjk_ranges=tuple((lo, hi) for lo, hi in raw["cjk_ranges"]),
        metrics=Metrics(**raw["metrics"]),
        output_dir=root / raw["build"]["output_dir"],
        jobs=int(raw["build"]["jobs"]),
    )
