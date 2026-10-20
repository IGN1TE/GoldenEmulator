# GoldenEmulator

Windows-only emulator frontend with the approved Neon Arcade design.

## Stage 3 — emulator integration review

Stages 1 and 2 were approved by Cory on 2026-10-20. This stage adds a native Windows launcher, emulator selection, full game paths, process launch/status handling and persistent library/settings in the Windows user profile.

Use the **Stage 3 Windows review** prerelease under **Releases**. Extract the ZIP and run `GoldenEmulator.exe`, then **Settings → Emulator setup**. Select installed Dolphin, Xenia or PCSX2 executables, import a game folder, open a game, and choose **Launch game**.

The EXE hosts the interface in your browser; it is a portable review build, not the final installer. The root HTML alone remains a browser preview and cannot launch emulators.

### Integrations

| Console | Emulator | Launch preset |
|---|---|---|
| GameCube | Dolphin | `-b -e` followed by the game path |
| Xbox 360 | Xenia | Game path as a single argument |
| PlayStation 2 | PCSX2 | `-batch --` followed by the game path |
| PlayStation 5 | None connected | Library only; launch disabled |

Presets are based on the official [Dolphin readme](https://github.com/dolphin-emu/dolphin/blob/master/Readme.md), [Xenia options](https://github.com/xenia-project/xenia/wiki/Options) and [PCSX2 CLI documentation](https://pcsx2.net/docs/advanced/cli/). Set up and test your emulators independently first. No emulators, games, firmware or BIOS files are bundled.

### Existing Stage 2 library

Export a backup in Stage 2, restore it in Stage 3, then use **Locate game file** for each entry. Native imports link full Windows paths immediately. Backups include metadata, full/relative paths and cover artwork, not game files. Emulator EXE settings are separate and must be configured on each PC.

Data lives in `%LOCALAPPDATA%\GoldenEmulator`. The launcher binds only to `127.0.0.1:48761`, checks a per-session token and request origin, and starts emulators without a command shell. Use one app window at a time. **Settings → Exit GoldenEmulator** closes the launcher without killing running emulators.

### Build and verification

`GoldenEmulator.py` is the native launcher; `test_native.py` tests it. The Stage 3 source ZIP includes editable frontend source, build script and JavaScript tests. Run `python -m unittest -v test_native.py` and, inside the extracted source, `node --test tests/library.test.cjs`. `python build.py` regenerates the self-contained HTML.

The GitHub Windows build workflow runs the tests, packages the app with PyInstaller and checks that the packaged executable can load its bundled interface and Tkinter. Test results are available under Actions. Real Dolphin/Xenia/PCSX2 gameplay, native picker behaviour and the rendered layout still need testing on Cory’s Windows PC. A successful process start is not proof of gameplay compatibility.

Stage 3 requires Cory’s approval before Stage 4 (controller experience). Stage 5 covers the installer and final polish. See ROADMAP.md and Issues for reviews.
