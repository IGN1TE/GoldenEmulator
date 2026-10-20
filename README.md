# GoldenEmulator

A **Windows-only** emulator frontend with the selected Neon Arcade design: dark navy, purple/cyan accents and scrolling console cards.

## Stage 2: game library — ready for review

Cory approved Stage 1 on 2026-10-20. Stage 2 adds real folder scanning, an import preview, duplicate filtering, locally saved library entries, custom covers, editable titles/notes, search, console filters, sorting, favourites, removal and backup export/restore.

This remains a browser-based review build for the planned Windows desktop app. Emulator launching comes in Stage 3, after Stage 2 approval.

## Try it on Windows

1. Download **GoldenEmulator-Stage-2-Windows.zip** from this repository.
2. Extract it to a permanent folder and open **GoldenEmulator.html** in Edge or Chrome.
3. Choose **Import game folder**, select a console, choose its folder, review the results and add selected games.
4. Open a game to edit details and artwork. Use **Settings → Export backup** before moving the app or clearing browser data.

The same HTML is available at the repository root. F11 enables fullscreen. See START-HERE.txt for supported formats, limits and the review checklist in ROADMAP.md. Stage 1’s original ZIP remains available.

## Storage and boundaries

Game files are not copied or uploaded. IndexedDB stores metadata and resized cover artwork in this browser. Only relative paths are available; full Windows paths and emulator launch configuration come later. Use one app window at a time. PS5 file recognition is not a compatibility claim. Samples are available separately under Settings → View demo library.

## Source and validation

The root HTML is self-contained source. **GoldenEmulator-Stage-2-Source.zip** also contains editable JS/CSS, the original embedded artwork, a Python build script and automated tests. Extract it, run `python build.py` to build the HTML and `node --test tests/library.test.cjs` to run tests.

Eight import/backup/escaping tests and JavaScript syntax checks pass. Actual browser rendering, folder-picker UI, IndexedDB persistence and Windows runtime remain unverified here: cloud browser policy blocks local file previews. These are part of the Stage 2 user review, not claimed as tested.

See Issues for stage feedback. Every stage requires Cory’s approval before the next begins.
