"""Render a PNG specimen with a cell grid to eyeball the 2:1 alignment. Needs Pillow."""

from __future__ import annotations

from pathlib import Path

GRID_LINES = (
    "|0123456789|abcdefghij|",
    "|가나다라마|바사아자차|",
    "|漢字學習中|簡体中文字|",
    "|ひらがなカ|タカナ日本|",
    "|ｱｲｳｴｵｶｷｸｹｺ|ﾊﾝｶｸｶﾅ1234|",
    "|ＡＢＣ１２|「」、。？|",
    "|     |\U000f0219 \U000f02a2    |",
)
TEXT_LINES = (
    "JetKai Mono  0O 1lI {}[]() -> => != === <= >= :: |> //",
    "다람쥐 헌 쳇바퀴에 타고파. 한글 코딩 폰트 테스트 012345",
    "いろはにほへと ちりぬるを。日本語のテキストとカタカナ",
    "天地玄黃 宇宙洪荒。简体中文测试：这个们说话。繁體中文",
)


def render(font_path: Path, out: Path, size: int = 32) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(font_path), size)
    cell = font.getlength("0")
    line_h = int(size * 1.6)
    cols = round(max(font.getlength(l) for l in GRID_LINES) / cell)
    width = int(max(font.getlength(l) for l in GRID_LINES + TEXT_LINES)) + 40
    height = line_h * (len(GRID_LINES) + len(TEXT_LINES) + 2) + 20
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)

    d.text((20, 10), font_path.name, fill=(130, 130, 130), font=ImageFont.truetype(str(font_path), 18))
    y = 10 + line_h
    grid_top = y
    for line in GRID_LINES:
        d.text((20, y), line, fill="black", font=font)
        y += line_h
    for col in range(0, cols + 1, 2):  # one guide every two cells
        x = 20 + col * cell
        d.line([(x, grid_top - 4), (x, y - 8)], fill=(255, 190, 190), width=1)
    y += line_h // 2
    for line in TEXT_LINES:
        d.text((20, y), line, fill="black", font=font)
        y += line_h

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
