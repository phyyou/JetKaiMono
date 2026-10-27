"""Layered merge of WenKai CJK glyphs into a JetBrains Mono Nerd Font base."""

from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

from .config import Config

# Tables in the Nerd Font base that make no sense after merging.
DROP_TABLES = ("PfEd", "DSIG")


def target_cells(codepoint: int, source_cells: int) -> int:
    """Cells a glyph should occupy, following East Asian Width like terminals do."""
    if source_cells == 0:
        return 0  # combining marks stay zero-width
    if unicodedata.category(chr(codepoint)) == "Cn":
        return source_cells  # newer than this Python's Unicode data, which would say "N"
    eaw = unicodedata.east_asian_width(chr(codepoint))
    if eaw in ("W", "F"):
        return 2
    if eaw in ("H", "Na", "N"):
        return 1
    return source_cells  # Ambiguous: keep the source design


@dataclass
class LayerReport:
    name: str
    codepoints: int = 0
    glyphs: int = 0
    replaced_base: int = 0  # base codepoints taken over because they are East Asian Wide
    squeezed: int = 0  # wide designs narrowed to fit one cell
    widened: int = 0  # narrow designs centred in two cells


def _layer_codepoints(
    source: TTFont, config: Config, base_cmap: dict[int, str], claimed: set[int]
) -> tuple[dict[str, list[int]], int]:
    """Group the codepoints this layer will supply by source glyph name."""
    by_glyph: dict[str, list[int]] = defaultdict(list)
    replaced = 0
    for cp, name in source.getBestCmap().items():
        if cp in claimed or not config.in_cjk_ranges(cp):
            continue
        if cp in base_cmap:
            if unicodedata.east_asian_width(chr(cp)) not in ("W", "F"):
                continue
            replaced += 1
        by_glyph[name].append(cp)
    return by_glyph, replaced


def merge_cjk(base: TTFont, sources: list[tuple[str, TTFont]], config: Config) -> list[LayerReport]:
    """Copy CJK glyphs from each source (in priority order) into base, resized to 1 or 2 cells."""
    m = config.metrics
    base_upm = base["head"].unitsPerEm
    base_cmap = base.getBestCmap()
    cmap = dict(base_cmap)
    names = set(base.getGlyphOrder())
    claimed: set[int] = set()
    added = []  # (first codepoint, name, glyph, advance)
    reports = []

    for layer_name, source in sources:
        report = LayerReport(layer_name)
        by_glyph, report.replaced_base = _layer_codepoints(source, config, base_cmap, claimed)

        upm = source["head"].unitsPerEm
        half_em = upm / 2
        os2 = source["OS/2"]
        em_center_y = (os2.sTypoAscender + os2.sTypoDescender) / 2
        scale = m.cjk_scale * base_upm / upm
        dy = m.cjk_center_y - em_center_y * scale
        glyph_set = source.getGlyphSet()
        hmtx = source["hmtx"]

        for src_name, cps in by_glyph.items():
            cps.sort()
            src_advance = hmtx[src_name][0]
            src_cells = round(src_advance / half_em)
            cells = target_cells(cps[0], src_cells)
            advance = cells * m.cell_width

            sx = scale
            if src_cells and cells < src_cells:
                sx *= cells / src_cells  # squeeze, or it would spill into the next cell
                report.squeezed += 1
            elif src_cells and cells > src_cells:
                report.widened += 1  # stretching looks wrong; centring is enough
            # Zero-width marks are drawn over the preceding full-width glyph.
            src_center_x = src_advance / 2 if src_advance else -half_em
            center_x = advance / 2 if advance else -m.cell_width
            dx = center_x - src_center_x * sx

            recording = DecomposingRecordingPen(glyph_set)
            glyph_set[src_name].draw(recording)
            pen = TTGlyphPen(None)
            recording.replay(TransformPen(pen, (sx, 0, 0, scale, dx, dy)))
            glyph = pen.glyph()

            name = src_name if src_name not in names else _unique(f"{src_name}.cjk", names)
            names.add(name)
            added.append((cps[0], name, glyph, advance))
            for cp in cps:
                cmap[cp] = name
            claimed.update(cps)
            report.codepoints += len(cps)
            report.glyphs += 1
        reports.append(report)

    _install_glyphs(base, added)
    _rebuild_cmap(base, cmap)
    _finish_tables(base)
    return reports


def _unique(name: str, names: set[str]) -> str:
    candidate, i = name, 2
    while candidate in names:
        candidate, i = f"{name}{i}", i + 1
    return candidate


def _install_glyphs(font: TTFont, added: list) -> None:
    glyf, hmtx = font["glyf"], font["hmtx"]
    order = list(font.getGlyphOrder())
    # Appending in codepoint order keeps glyph IDs contiguous, which keeps cmap format 4 small.
    for _, name, glyph, advance in sorted(added, key=lambda a: a[0]):
        glyf.glyphs[name] = glyph
        lsb = 0
        if glyph.numberOfContours:
            glyph.recalcBounds(glyf)
            lsb = glyph.xMin
        hmtx.metrics[name] = (advance, lsb)
        order.append(name)
    if len(order) > 0xFFFF:
        raise ValueError(f"{len(order)} glyphs exceeds the TrueType limit of 65535")
    font.setGlyphOrder(order)
    glyf.setGlyphOrder(order)


def _rebuild_cmap(font: TTFont, cmap: dict[int, str]) -> None:
    bmp = {cp: g for cp, g in cmap.items() if cp <= 0xFFFF}
    tables = [t for t in font["cmap"].tables if t.platformID == 1]  # keep the legacy Mac Roman table
    for platform_id, encoding_id, fmt, mapping in (
        (0, 3, 4, bmp),
        (0, 4, 12, cmap),
        (3, 1, 4, bmp),
        (3, 10, 12, cmap),
    ):
        table = CmapSubtable.newSubtable(fmt)
        table.platformID, table.platEncID, table.language = platform_id, encoding_id, 0
        table.cmap = dict(mapping)
        tables.append(table)
    font["cmap"].tables = tables


def _finish_tables(font: TTFont) -> None:
    for tag in DROP_TABLES:
        if tag in font:
            del font[tag]
    os2 = font["OS/2"]
    # xAvgCharWidth stays at one cell: some terminals size their grid from it.
    os2.recalcUnicodeRanges(font)
    os2.recalcCodePageRanges(font)
