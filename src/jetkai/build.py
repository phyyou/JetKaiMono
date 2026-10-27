"""Build every (variant, style) pair, optionally in parallel."""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from fontTools.ttLib import TTFont

from .config import Config
from .merge import merge_cjk
from .naming import combined_copyright, postscript_name, set_names


def build_one(config: Config, variant_key: str, style_key: str) -> tuple[Path, str]:
    variant, style = config.variants[variant_key], config.styles[style_key]
    started = time.monotonic()

    base = TTFont(config.base_path(variant, style))
    sources = [
        (layer.name, TTFont(config.layer_path(layer, style), lazy=True)) for layer in config.layers
    ]
    reports = merge_cjk(base, sources, config)
    set_names(
        base,
        variant.family,
        style,
        config,
        combined_copyright(config.author, [base] + [font for _, font in sources]),
    )

    out_dir = config.output_dir / "ttf"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{postscript_name(variant.family, style)}.ttf"
    base.save(out)
    for _, font in sources:
        font.close()

    lines = [f"{out.name}  ({time.monotonic() - started:.0f}s, {len(base.getGlyphOrder())} glyphs)"]
    for r in reports:
        lines.append(
            f"    {r.name}: {r.codepoints} codepoints / {r.glyphs} glyphs"
            f" (replaced base: {r.replaced_base}, squeezed: {r.squeezed}, widened: {r.widened})"
        )
    return out, "\n".join(lines)


def build_all(config: Config, variants: list[str], styles: list[str], jobs: int) -> list[Path]:
    for path in [config.base_path(config.variants[v], config.styles[s]) for v in variants for s in styles] + [
        config.layer_path(layer, config.styles[s]) for layer in config.layers for s in styles
    ]:
        if not path.exists():
            raise SystemExit(f"missing source {path}; run `jetkai fetch` first")

    pairs = [(v, s) for v in variants for s in styles]
    print(f"Building {len(pairs)} fonts with {jobs} job(s)")
    outputs = []
    if jobs <= 1:
        for v, s in pairs:
            out, log = build_one(config, v, s)
            print(log)
            outputs.append(out)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = [pool.submit(build_one, config, v, s) for v, s in pairs]
            for future in as_completed(futures):
                out, log = future.result()
                print(log, flush=True)
                outputs.append(out)
    return sorted(outputs)
