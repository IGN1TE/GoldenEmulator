# GoldenEmulator 0.7.0

Fixes stretched console artwork during expansion and selection. Adds SNES (Snes9x), NES (Mesen), Wii (Dolphin), PS1 (DuckStation), PS3 (RPCS3), and experimental PS4 (Kyty --game).

Download GoldenEmulator-Setup-0.7.0.exe from Releases, exit the old app and install. Settings > Check for updates also discovers this release. The standalone desktop window, gold logo, controller navigation, library, artwork, favourites, notes and existing emulator paths are retained. User data stays in %LOCALAPPDATA%\GoldenEmulator with the same version-2 schema.

Choose installed EXEs under Settings > Emulator setup. Configure BIOS, firmware and controllers in each emulator first. No emulators, firmware or games are included.

Supported imports: SNES SFC/SMC; NES NES/UNF/UNIF; Wii ISO/WBFS/RVZ/CISO; PS1 CUE/CHD/PBP/M3U; PS3 EBOOT.BIN/ELF/SELF; PS4 eboot.bin/ELF/ZAR. Existing GameCube, Xbox 360 and PS2 formats remain. Install PS3 packages in RPCS3 first. PS4 PKG installation is not supported.

The installed Kyty build inspected reports version 0.3.0 / git 1a053f9 and accepts --game <dir|elf|zar>. Choose kyty_emulator.exe, not its launcher or updater. GoldenEmulator verifies this interface when connecting and launching. Original Lua-based Kyty builds are not supported by this preset. Argument support does not establish game compatibility. PS5 remains library-only, with launching disabled; no PS5 gameplay compatibility is claimed.

Upstream reference: https://github.com/InoriRus/Kyty. Its experimental claims do not establish compatibility of installed forks or particular games.

Editable sources are now tracked in src/, build.py and tests/. Run python build.py, python -m unittest test_native.py, and node --test tests/*.test.cjs. Windows packaging uses PyInstaller 6.16.0, pywebview 6.2.1 and Inno Setup. The workflow checks branding, desktop readiness, second launch, shutdown, reinstall/uninstall and saved-data preservation before publishing. Executables remain unsigned.
