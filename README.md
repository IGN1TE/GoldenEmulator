# GoldenEmulator 0.9.0

A Windows desktop launcher for your own installed emulators and game library. Download **GoldenEmulator-Setup-0.9.0.exe** from [Releases](https://github.com/IGN1TE/GoldenEmulator/releases/latest), close the old app and install. Settings → Check for updates shows release notes, downloads and verifies the official installer, and reopens the app after installation.

## Library Hub

Use **Hub** in the toolbar for watched folders, missing-file repair, custom collections, emulator health checks, diagnostics, updates and couch mode. Open a game and choose **Game page & settings** for artwork/metadata lookup, rating, completion status, screenshots, per-game launch settings, playtime, save backups and multi-disc grouping. See [release-notes.md](release-notes.md) for the complete 15-feature list and operational limits.

Watched folders optionally scan once a minute while the app is open; new games wait for review. Portable links record a watched root plus a relative path. Reconnect a moved root and review repairs. Metadata searches send the title to Wikimedia, never local paths, and require choosing a match. Artwork availability varies.

Select each game's save folder before creating backups. Close the emulator before backing up/restoring. Restoration creates a safety ZIP and overwrites matching files; unrelated files remain. Optional automatic backup runs before launch. Playtime records the emulator process while GoldenEmulator stays open, including menus and pauses; hand-off launchers are excluded.

The library stays in `%LOCALAPPDATA%\GoldenEmulator` with schema version 2. Hub data uses `features.json`; save archives use `save-backups`. The existing library backup and Hub export are separate. Hub restore imports descriptions, ratings, collections and screenshots for matching IDs; select executable, configuration and save paths locally on each machine. Moving your full data folder retains session history and portable bindings; reconnect roots afterwards.

Controller controls: D-pad/left stick navigate, A/Cross select, B/Circle back, LB/RB switch pages, Y/Triangle open search keyboard, X/Square open Hub, Start/Menu cycle collections. Keyboard/mouse controls remain available. Fullscreen and couch mode are independent settings.

## Emulator setup

Choose installed EXEs under Settings → Emulator setup. Configure BIOS, firmware, graphics and controllers in each emulator. Health checks verify executable presence and provide setup guidance; they do not validate firmware or compatibility. No emulators, firmware or games are included.

Supported presets: Dolphin (GameCube/Wii), Xenia (Xbox 360), PCSX2 (PS2), Snes9x (SNES), Mesen (NES), DuckStation (PS1), RPCS3 (PS3), and shadPS4 (PS4). PS3 uses extracted EBOOT.BIN/ELF/SELF; install packages and firmware in RPCS3. PS4 uses shadPS4.exe (`-g game`) or ShadPS4QtLauncher.exe (`-d -g game`) with extracted eboot.bin/ELF. Other PS4 EXEs and PS5 custom EXEs open their interface only; load games there. A connected EXE does not establish playable compatibility.

## Development

Editable sources are in `src/`, `GoldenEmulator.py` and `features.py`. `python build.py` generates the self-contained UI. Run `python -m unittest -v test_native.py test_features.py` and `node --test tests/*.test.cjs`. Browser checks use Playwright: `node --test tests/*.browser.cjs` after installing Chromium. Windows CI also verifies packaged runtime, installer, relaunch, shutdown, uninstall and saved-data preservation before publishing. Packaging uses PyInstaller, pywebview and Inno Setup. Executables are unsigned.
