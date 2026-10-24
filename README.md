# GoldenEmulator 0.8.1

Fixes the console carousel jumping back when moving between emulators, while preserving proportional artwork during expansion and selection. Adds SNES (Snes9x), NES (Mesen), Wii (Dolphin), PS1 (DuckStation), PS3 (RPCS3), and experimental PS4 (Kyty --game).

Download GoldenEmulator-Setup-0.8.1.exe from Releases, exit the old app and install. Settings > Check for updates also discovers this release. The standalone desktop window, gold logo, controller navigation, library, artwork, favourites, notes and existing emulator paths are retained. User data stays in %LOCALAPPDATA%\GoldenEmulator with the same version-2 schema.

Choose installed EXEs under Settings > Emulator setup. Configure BIOS, firmware and controllers in each emulator first. No emulators, firmware or games are included.

Supported imports: SNES SFC/SMC; NES NES/UNF/UNIF; Wii ISO/WBFS/RVZ/CISO; PS1 CUE/CHD/PBP/M3U; PS3 EBOOT.BIN/ELF/SELF; PS4 eboot.bin/ELF/ZAR. Existing GameCube, Xbox 360 and PS2 formats remain. Install PS3 packages in RPCS3 first. PS4 PKG installation is not supported.

PS4 uses shadPS4.exe (-g game) or ShadPS4QtLauncher.exe (-d -g game). Choose the installed EXE in Settings. Other EXEs open without game arguments. PS5 retains its separate custom emulator connection.

shadPS4 references: https://github.com/shadps4-emu/shadPS4 and https://github.com/shadps4-emu/shadps4-qtlauncher. Game compatibility depends on your installed build.

Editable sources are now tracked in src/, build.py and tests/. Run python build.py, python -m unittest test_native.py, and node --test tests/*.test.cjs. Windows packaging uses PyInstaller 6.16.0, pywebview 6.2.1 and Inno Setup. The workflow checks branding, desktop readiness, second launch, shutdown, reinstall/uninstall and saved-data preservation before publishing. Executables remain unsigned.

Version 0.8.1: PS5 setup accepts KYTY or another installed EXE. Open emulator starts its interface; load games there. Check for updates downloads and verifies the official installer, runs it and reopens the app. The first upgrade from older versions still needs the new installer.
