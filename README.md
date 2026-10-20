# GoldenEmulator 0.6.0

GoldenEmulator 0.6.0 opens its complete interface in its own desktop window. Opening the app no longer opens Opera, Edge or another browser tab.

Download **GoldenEmulator-Setup-0.6.0.exe**, exit the older version, and run the installer. Use your GoldenEmulator desktop or Start menu shortcut. Existing library entries, artwork and emulator paths are retained.

Closing the GoldenEmulator window exits the app and local service. Opening the shortcut again restores an existing desktop window. Settings includes Check for updates and Exit GoldenEmulator. Fullscreen uses the desktop window. Controller navigation and installed Dolphin/Xenia/PCSX2 integration are retained.

The installer includes Microsoft's signed WebView2 bootstrapper and installs the runtime if missing (internet required in that case). The portable ZIP requires WebView2 already installed. External update-download pages still open in your browser; the game library stays in the app.

Windows checks cover actual desktop UI rendering, Gamepad API availability, installation, repeated opening, stop command, window closing, reinstall/uninstall and library preservation. Physical controllers, file picking and gameplay still need user review in this new desktop host.

Publisher branding remains IGN1TE. Code signing is deferred as requested; the installer remains unsigned and may show SmartScreen warnings. PS5 remains library-only.

Full source: GoldenEmulator-Desktop-0.6.0-Source.zip. Build HTML with python build.py. Windows packaging uses PyInstaller, pywebview 6.2.1 and Inno Setup.
