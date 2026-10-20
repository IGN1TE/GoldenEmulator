# GoldenEmulator project stages

Platform: Windows only. Design: Neon Arcade, with dark navy, purple and cyan accents, a console carousel and recently played games.

Each stage requires Cory’s review and explicit approval before work advances to the next stage.

| Stage | Scope | Status |
| --- | --- | --- |
| 1. Interface prototype | Clickable interface, console selection, navigation, sample search and favourites | Awaiting user review |
| 2. Game library | Import game folders, artwork, search, favourites and game details | Pending Stage 1 approval |
| 3. Emulator integration | Connect installed emulators and launch games; test each system separately | Pending Stage 2 approval |
| 4. Controller experience | Controller navigation, fullscreen and returning after gameplay | Pending Stage 3 approval |
| 5. Installation and polish | Windows installer, saved settings, error handling and PC testing | Pending Stage 4 approval |

## Stage 1 review checklist

- [ ] Review layout, spacing, colours and artwork against the chosen concept.
- [ ] Check console carousel and navigation.
- [ ] Check sample search, game details and favourites.
- [ ] Verify layout in Edge or Chrome on Windows and at different window sizes.
- [ ] Record feedback and resolve requested changes.
- [ ] Obtain Cory’s explicit approval for Stage 2.

Stage 1 is a browser prototype, not the packaged Windows app. Syntax and stub-based checks passed during its original build. Browser rendering and Windows runtime testing remain unverified because the test browser download failed. Emulator launching is not implemented. PS5 compatibility depends on the underlying emulator; the interface does not imply playable support.
