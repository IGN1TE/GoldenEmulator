# GoldenEmulator project stages

Platform: Windows only. Design: Neon Arcade, with dark navy, purple and cyan accents, a console carousel and recently played games.

Each stage requires Cory’s review and explicit approval before work advances to the next stage.

| Stage | Scope | Status |
| --- | --- | --- |
| 1. Interface prototype | Clickable interface, console selection, navigation, sample search and favourites | Approved by Cory on 2026-10-20 |
| 2. Game library | Import game folders, artwork, search, favourites and game details | Approved by Cory on 2026-10-20 |
| 3. Emulator integration | Connect installed emulators and launch games; test each system separately | Approved by Cory on 2026-10-20: everything worked |
| 4. Controller experience | Controller navigation, fullscreen and returning after gameplay | Approved by Cory on 2026-10-20: controller works |
| 5. Installation and polish | Windows installer, saved settings, error handling and PC testing | Stage 5 installer delivered; awaiting review |

## Stage 2 review checklist

- [ ] Import a folder for each console you use.
- [ ] Check recognised files, skipped files and duplicate handling.
- [ ] Edit a title, notes and cover image.
- [ ] Search, filter, sort and favourite imported games.
- [ ] Close/reopen the same HTML in the same browser and verify persistence.
- [ ] Export a backup, remove an entry, then restore the backup.
- [ ] Review layout on Windows and provide screenshots of issues.
- [ ] Obtain Cory’s explicit approval before Stage 3.

## Stage 1 review checklist (approved)

- [ ] Review layout, spacing, colours and artwork against the chosen concept.
- [ ] Check console carousel and navigation.
- [ ] Check sample search, game details and favourites.
- [ ] Verify layout in Edge or Chrome on Windows and at different window sizes.
- [ ] Record feedback and resolve requested changes.
- [ ] Obtain Cory’s explicit approval for Stage 2.

Stage 1 is a browser prototype, not the packaged Windows app. Syntax and stub-based checks passed during its original build. Browser rendering and Windows runtime testing remain unverified because the test browser download failed. Emulator launching is not implemented. PS5 compatibility depends on the underlying emulator; the interface does not imply playable support.

## Stage 3 Windows review

- [ ] Configure installed Dolphin, Xenia and PCSX2 EXEs.
- [ ] Import native game folders, or restore Stage 2 backup and locate game files.
- [ ] Launch and exit a game for each configured system.
- [ ] Verify spaces in emulator/game paths work.
- [ ] Verify missing-file errors and duplicate-launch prevention.
- [ ] Reopen launcher and verify library/settings persist.
- [ ] Report game/emulator/version and errors for failed launches.
- [ ] Cory approves Stage 3 before controller work starts.

## Stage 4 review

- [ ] Connect controller and check status indicator.
- [ ] Browse systems, library, favourites and game details.
- [ ] Check A/Cross, B/Circle, LB/RB and dropdown editing.
- [ ] Hold directions, check stick drift and reconnect controller.
- [ ] Launch a game, close it normally and return to this tab.
- [ ] Verify no held button causes an accidental action on return.
- [ ] Cory approves before Stage 5.

## Stage 5 review

- [ ] Exit old launcher, install and open shortcut.
- [ ] Verify library and emulator paths are retained.
- [ ] Close launcher window and reopen successfully.
- [ ] Try Start menu Stop GoldenEmulator.
- [ ] Check controller navigation and a game launch.
- [ ] Cory reviews installer and final polish.

## Desktop correction — 0.6.0

User requested standalone desktop hosting after Stage 5. Full interface moved into WebView2 through pywebview. Retains library, controller logic and update check. Awaiting Windows desktop review. Signing deferred by user.
