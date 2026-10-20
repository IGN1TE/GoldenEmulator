# GoldenEmulator — Windows

Stage 5 adds a Windows installer and a visible launcher window.

Download **GoldenEmulator-Setup-0.5.0.exe** and run it. Setup installs for your Windows account, adds Start menu shortcuts and offers a desktop shortcut. No Python installation is required. The portable ZIP is also available.

**Updating from Stage 3 or 4:** first use Settings > Exit GoldenEmulator in the old browser tab. If you open the new version while an older launcher is running, it reopens the old tab and explains how to exit it. Then start the new installed shortcut. Existing library and emulator paths remain in your user profile.

The new launcher window has Open game library and Exit GoldenEmulator buttons. Closing that window exits the launcher. Closing only the browser tab does not exit it. You can also use Start menu > GoldenEmulator > Stop GoldenEmulator. Running emulators stay open when the launcher exits. Reopening the installed app while it is already running opens its library again.

The interface still uses your default browser. Controller navigation is retained. Text entry and file pickers use keyboard/mouse. Emulator gameplay controls are configured separately. PS5 remains library-only.

The build tests installation, installed EXE startup, repeated launch, the stop shortcut, closing the launcher window, reinstalling and uninstalling. Reinstall/uninstall preserve the saved library outside the installation folder. This unsigned review installer still needs Cory’s Windows review; updates are checked on demand.

## Development

The complete editable source is in GoldenEmulator-Stage-5-Source.zip. Run python build.py to regenerate GoldenEmulator.html. Run python -m unittest -v test_native.py and node --test tests/*.test.cjs. GitHub Actions packages the EXE with PyInstaller and the installer with Inno Setup, tests them on Windows and publishes only after success.

Check for updates is available in the launcher window and Settings. It compares installer versions on GitHub, reports when you are up to date, and offers the download page for newer versions, including review releases. Installation remains manual.
