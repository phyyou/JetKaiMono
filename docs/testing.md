# Testing JetKai Mono in real apps

Use [`docs/specimen.txt`](specimen.txt) as the test text; block numbers [1]–[6] below refer to it.
When something looks wrong, note the **app and version, font size, specimen line, and a screenshot**.

## 0. Installation

- [ ] Font Book lists `JetKai Mono` and `JetKai Mono NL`, each with eight styles
- [ ] Font Book's preview shows Hangul, kana and Han in JetKai, not a fallback font

## 1. Ghostty

Set the font in your Ghostty config, then reload it with `Cmd+Shift+,`:

```
font-family = "JetKai Mono"
```

- [ ] `cat docs/specimen.txt`: every `|` in block [1] lines up
- [ ] [1] Halfwidth katakana (`ｱｲｳ...`) take one cell each, fullwidth letters (`ＡＢＣ`) two
- [ ] [2] Ligatures render (`->`, `!=`, `===`) and come apart with `font-family = "JetKai Mono NL"`
- [ ] Korean IME: the character being composed (`ㅎ` → `하` → `한`) shows at the cursor, two cells wide
- [ ] The cursor block is two cells wide over Hangul
- [ ] Hangul and Han are neither too large nor too small next to Latin, and not shifted up or down
- [ ] At Regular, Latin and Hangul strokes look about equally heavy
- [ ] At Bold (e.g. bold `ls` colours, nvim highlights), note how much lighter Hangul looks (known limitation)
- [ ] Alignment survives font size changes (`Cmd +` / `Cmd -`)

Ghostty draws box drawing, block elements and Powerline shapes with its own renderer, not the font.
Check those glyphs in VS Code instead. Ghostty also rescales Nerd Font icons, so they may look
different from VS Code.

## 2. CLI tools inside the terminal

- [ ] **starship:** Nerd Font icons and Powerline separators are not clipped or overlapping
- [ ] **lsd / eza:** `lsd -l` icons fit in one cell and don't overlap the file name
- [ ] **nvim:** on lines mixing Hangul and Latin, cursor movement and visual block selection (`Ctrl-v`) stay on the right columns
- [ ] **tmux:** split panes with Hangul content keep their borders in place
- [ ] **macOS Korean file names (NFD):** files named in Finder are stored as NFD. Note whether `ls`/`lsd` shows separated jamo and how distracting it is

  Create an NFD file name to test with:

  ```bash
  mkdir -p /tmp/jetkai-nfd && touch "/tmp/jetkai-nfd/$(python3 -c 'import unicodedata; print(unicodedata.normalize("NFD", "한글 파일.txt"))')" && ls /tmp/jetkai-nfd
  ```

## 3. VS Code

Put JetKai first in `settings.json`. Switching back and forth with your previous CJK font makes differences easy to see.

```json
"editor.fontFamily": "'JetKai Mono'",
"editor.fontLigatures": true,
"terminal.integrated.fontFamily": "'JetKai Mono'",
```

- [ ] `docs/specimen.txt` block [1] lines up
- [ ] [1] Box drawing lines (`──────────`, `━━━━━━━━━━`) join without gaps
- [ ] [2] Ligatures render and turn off with `"editor.fontLigatures": false`
- [ ] [3] Powerline arrow separators (U+E0B0) fill the full line height
- [ ] Italic theme scopes (comments etc.) slant Latin only; CJK stays upright (intended)
- [ ] `"editor.fontWeight": "300"` switches to Light, `"500"` to Medium
- [ ] Rulers (`editor.rulers`) and column positions match on lines with Korean comments
- [ ] Block [1] also lines up in the integrated terminal

## 4. Known limitations (not bugs)

- CJK in Bold styles uses WenKai Medium, so it looks lighter than bold Latin
- CJK stays upright in italic styles
- NFD Hangul (conjoining jamo) is not in JetKai and falls back to another font
- `※ ① ② ③ ★ ☆` in [5] are not in JetKai and fall back to another font; one or two cells depends on the terminal's ambiguous-width setting
- Han characters shared across languages use Korean glyph forms (e.g. `令`)

## 5. Results

| Item | Result | Notes |
|---|---|---|
| Terminal alignment | | |
| Ligatures | | |
| Korean IME input | | |
| CJK size and vertical position | | |
| Stroke weight (Regular / Bold) | | |
| Prompt and file icons | | |
| nvim / tmux | | |
| NFD file names | | |
| VS Code alignment and box drawing | | |
| VS Code weights and italics | | |
