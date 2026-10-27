"""Checks run against built fonts."""

from __future__ import annotations

import unicodedata
from pathlib import Path

from fontTools.ttLib import TTFont

from .config import Config

COVERAGE_BLOCKS = (
    ("Hangul Syllables", 0xAC00, 0xD7A3),
    ("Hangul Compatibility Jamo", 0x3131, 0x318E),
    ("Hiragana", 0x3041, 0x309F),
    ("Katakana", 0x30A0, 0x30FF),
    ("Katakana Phonetic Ext", 0x31F0, 0x31FF),
    ("Halfwidth Katakana", 0xFF61, 0xFF9F),
    ("CJK Symbols & Punctuation", 0x3000, 0x303F),
    ("CJK Unified Ideographs", 0x4E00, 0x9FFF),
    ("CJK Ext-A", 0x3400, 0x4DBF),
    ("CJK Ext-B", 0x20000, 0x2A6DF),
    ("CJK Compatibility Ideographs", 0xF900, 0xFAFF),
    ("Bopomofo", 0x3105, 0x312F),
)


def _assigned(lo: int, hi: int) -> int:
    return sum(1 for cp in range(lo, hi + 1) if unicodedata.category(chr(cp)) != "Cn")


def verify_font(path: Path, config: Config) -> list[str]:
    """Print a report for one font and return the list of failures."""
    cell = config.metrics.cell_width
    font = TTFont(path)
    font.ensureDecompiled()  # every table must parse back
    cmap = font.getBestCmap()
    hmtx, glyf = font["hmtx"], font["glyf"]
    os2, post = font["OS/2"], font["post"]
    failures = []

    print(f"== {path.name}")
    num_glyphs = len(font.getGlyphOrder())
    print(f"  glyphs: {num_glyphs}  codepoints: {len(cmap)}")
    if num_glyphs > 0xFFFF:
        failures.append(f"{num_glyphs} glyphs exceeds 65535")

    widths = {hmtx[name][0] for name in font.getGlyphOrder()}
    odd = widths - {0, cell, 2 * cell}
    if odd:
        failures.append(f"advance widths outside 0/{cell}/{2 * cell}: {sorted(odd)[:10]}")

    # Terminals lay text out by East Asian Width; CJK advances must agree.
    # Outside the CJK ranges the glyphs are JetBrains Mono's own and are only reported.
    wrong, wrong_base = [], []
    for cp, name in cmap.items():
        advance = hmtx[name][0]
        if advance == 0 or unicodedata.category(chr(cp)) == "Cn":
            continue
        eaw = unicodedata.east_asian_width(chr(cp))
        expected = {"W": 2, "F": 2, "H": 1, "Na": 1}.get(eaw)
        if expected is not None and advance != expected * cell:
            (wrong if config.in_cjk_ranges(cp) else wrong_base).append(f"U+{cp:04X}({eaw})={advance}")
    if wrong:
        failures.append(f"{len(wrong)} CJK codepoints disagree with East Asian Width: {wrong[:8]}")
    print(f"  base glyphs disagreeing with East Asian Width (left as designed): {wrong_base[:8]}")

    clipped = [
        f"U+{cp:04X}"
        for cp, name in cmap.items()
        if config.in_cjk_ranges(cp)
        and hmtx[name][0]  # zero-width tone marks sit outside the line on purpose
        and glyf[name].numberOfContours
        and (glyf[name].yMax > os2.usWinAscent or glyf[name].yMin < -os2.usWinDescent)
    ]
    if clipped:
        failures.append(f"{len(clipped)} CJK glyphs exceed usWin ascent/descent: {clipped[:8]}")

    for table in font["cmap"].tables:
        if table.format == 4 and len(table.compile(font)) > 0xFFFF:
            failures.append(f"cmap format 4 ({table.platformID},{table.platEncID}) overflows 64 KiB")

    print(f"  isFixedPitch={post.isFixedPitch} xAvgCharWidth={os2.xAvgCharWidth} "
          f"weight={os2.usWeightClass} fsSelection={os2.fsSelection:#06x}")
    name = font["name"]
    print(f"  names: {name.getDebugName(1)!r} / {name.getDebugName(2)!r}; "
          f"typographic {name.getDebugName(16)!r} / {name.getDebugName(17)!r}; ps {name.getDebugName(6)!r}")
    for label, lo, hi in COVERAGE_BLOCKS:
        have = sum(1 for cp in cmap if lo <= cp <= hi)
        print(f"  {label:30s} {have:6d} / {_assigned(lo, hi)}")

    for f in failures:
        print(f"  FAIL: {f}")
    font.close()
    return failures


def verify_all(paths: list[Path], config: Config) -> bool:
    failures = {p: verify_font(p, config) for p in paths}
    bad = [p for p, f in failures.items() if f]
    print(f"\n{len(paths) - len(bad)}/{len(paths)} fonts passed")
    return not bad
