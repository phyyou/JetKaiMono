"""name table and font revision."""

from __future__ import annotations

from fontTools.ttLib import TTFont

from .config import Config, Style

RIBBI = {"Regular", "Italic", "Bold", "Bold Italic"}
LICENSE = (
    "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
    "This license is available with a FAQ at: https://openfontlicense.org"
)
LICENSE_URL = "https://openfontlicense.org"


def subfamily(style: Style) -> str:
    if not style.italic:
        return style.weight
    return "Italic" if style.weight == "Regular" else f"{style.weight} Italic"


def postscript_name(family: str, style: Style) -> str:
    return f"{family.replace(' ', '')}-{subfamily(style).replace(' ', '')}"


def combined_copyright(author: str, fonts: list[TTFont]) -> str:
    """Our notice plus every source notice. OFL requires keeping the originals."""
    lines = [f"JetKai Mono: Copyright 2026 {author}."]
    for font in fonts:
        notice = font["name"].getDebugName(0) or ""
        for line in notice.splitlines():
            if line.strip() and line.strip() not in lines:
                lines.append(line.strip())
    return "\n".join(lines)


def set_names(font: TTFont, family: str, style: Style, config: Config, copyright_notice: str) -> None:
    sub = subfamily(style)
    if sub in RIBBI:
        legacy_family, legacy_sub = family, sub
    else:
        # Non-RIBBI weights get their own legacy family so old apps can still pick them.
        legacy_family = f"{family} {style.weight}"
        legacy_sub = "Italic" if style.italic else "Regular"
    ps = postscript_name(family, style)

    entries = {
        0: copyright_notice,
        1: legacy_family,
        2: legacy_sub,
        3: f"{config.version};{ps}",
        4: f"{family} {sub}",
        5: f"Version {config.version}",
        6: ps,
        8: config.author,
        9: "JetBrains Mono: Philipp Nurullin, Konstantin Bulenkov; Klee One: Frances Chau; "
        "LXGW WenKai: LXGW; Nerd Fonts: Ryan L McIntyre",
        10: config.description,
        11: config.url,
        13: LICENSE,
        14: LICENSE_URL,
    }
    if sub not in RIBBI:
        entries[16] = family
        entries[17] = sub

    table = font["name"]
    table.names = []
    for name_id, value in entries.items():
        table.setName(value, name_id, 3, 1, 0x409)

    # Style bits must match the legacy subfamily; the Nerd Font base leaves REGULAR unset on Light/Medium.
    bold, italic = "Bold" in legacy_sub, "Italic" in legacy_sub
    os2 = font["OS/2"]
    os2.fsSelection &= ~0b1100001  # ITALIC, BOLD, REGULAR
    os2.fsSelection |= (italic << 0) | (bold << 5) | ((not bold and not italic) << 6)
    font["head"].macStyle = (bold << 0) | (italic << 1)

    major, minor, *_ = (config.version.split(".") + ["0"])
    font["head"].fontRevision = float(f"{major}.{minor}")
