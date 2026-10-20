# GoldenEmulator

A Windows-only emulator frontend project with the selected **Neon Arcade** design: dark navy, purple/cyan accents, scrolling console cards, and recently played games.

## Current status: Stage 1 awaiting review

This build is a clickable browser prototype for reviewing the planned Windows desktop app. It includes console selection, navigation, sample game details, search and locally saved favourites. Emulator launching is not implemented.

## Try Stage 1 on Windows

1. Download `GoldenEmulator-Stage-1-Windows.zip` and extract it.
2. Open `GoldenEmulator.html` in Edge or Chrome, or use `Launch-GoldenEmulator.cmd`.
3. Press F11 for fullscreen.
4. Review the interface and report feedback in the Stage 1 issue.

The source HTML is self-contained and includes CSS, JavaScript and embedded concept artwork. Games and artwork are illustrative sample data. PS5 launch support depends on the underlying emulator’s actual capabilities.

## Development stages

See [ROADMAP.md](ROADMAP.md) and the repository Issues for the five review stages. Cory must approve each stage before development advances to the next.

## Validation limitations

Original build checks passed JavaScript syntax and state/render checks using DOM stubs. Actual browser rendering and Windows runtime testing remain unverified because the test browser download failed. Windows visual review is part of Stage 1 acceptance.
