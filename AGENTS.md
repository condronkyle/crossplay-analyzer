# Repository Guidelines

Contributor guide for the Crossplay Board Analyzer — a fully offline, deterministic Scrabble board parser. It reads NYT Crossplay screenshots, detects the 15×15 grid, OCRs tile letters, finds words, and runs a Quackle kibitz. **No OpenAI or external API is used.**

## Project Structure & Module Organization

- `index.html` — the entire app (HTML, CSS, and JavaScript in one file). All parsing logic lives here: grid detection, tile detection, letter OCR, and the Quackle integration.
- `manual.html` — alternate manual board-input page.
- `quackle.js`, `quackle.wasm`, `quackle.data` — the Quackle WASM engine and dictionary (loaded at runtime).
- `test_board.png`, `IMG_3046.png`, `IMG_3047.png`, `IMG_3048.png` — example screenshots used as test fixtures.
- `test_grid_detection.py` — offline grid-detection test (passes).
- `test_score_ocr.py` — header score-OCR regression test.
- `test_browser_pipeline.py` — browser-level parsing and Quackle regression test.

## Build, Test, and Development Commands

There is no build step — it is a static site.

```bash
python3 -m pip install -r requirements-test.txt  # use Python 3.10 or newer
python3 -m playwright install chromium
python3 -m http.server 8000   # serve the app locally, then open http://localhost:8000
python3 test_grid_detection.py  # grid/tile detection test (needs numpy, Pillow, scipy)
python3 test_score_ocr.py       # header score OCR regression test
python3 test_browser_pipeline.py  # real browser pipeline test (needs Playwright and Chromium)
```

## Coding Style & Naming Conventions

- JavaScript: 2-space indent, `camelCase` functions/variables.
- Python tests: 4-space indent, `snake_case`.
- No linter or formatter is configured; match the surrounding style.
- Keep the app self-contained in `index.html`; avoid adding external dependencies.

## Testing Guidelines

- Python tests live at the repo root (`test_*.py`) and run against the example screenshots.
- The JavaScript pipeline test loads all four screenshots in Chromium and checks the exact board, rack, scores, words, and Quackle output.
- New CV/OCR work should update or add a `test_*.py` so regressions are caught offline.
- `test_score_ocr.py` is the pass/fail gate for header score OCR.

## Commit & Pull Request Guidelines

- Commit messages use an imperative, descriptive subject (e.g., `Fix grid detection: ...`, `Add ...`, `Remove ...`) followed by a body explaining the change and validation results.
- Keep changes focused; reference the behavior being fixed or added.
- PRs should describe the change, the approach, and the validation performed (test counts, images used).
- Screenshots or test output are encouraged when changing parsing behavior.

## Architecture Overview

The pipeline is: **premium-label grid detection → blue/white tile detection → template-match letter and header-score OCR → word finding → Quackle kibitz**. Header scores are read automatically from the screenshot using the local digit templates.
