# Changelog

All notable changes to grabit are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.2] - 2026-10-29

### Changed

- Requires Python 3.11 or newer. Python 3.10 reached end of life in October
  2026, and current yt-dlp releases no longer support it.
- Depends on yt-dlp 2026.10.26 or newer, so fresh installs get the latest
  site fixes.

## [0.1.1] - 2026-10-23

### Added

- `grab --version`.
- The public API (`GrabOptions`, `download`, `probe`, ...) is importable
  directly from the `grabit` package.
- Clipboard fallback on Windows (`Get-Clipboard`) and Linux
  (`wl-paste`, `xclip`, `xsel`), in addition to macOS (`pbpaste`).
- `CONTRIBUTING.md`, `SECURITY.md`, and issue templates.

### Changed

- The distribution name on PyPI is now `grabit-dl`. The commands stay `grab`
  and `grab-web`, and the import name stays `grabit`. The plain `grabit` name
  on PyPI already belongs to an unrelated project.
- The local web UI rejects requests with a foreign `Host` or `Origin`,
  requires a JSON content type, and caps request bodies. Binding it to a
  non-loopback address now prints a warning.

### Fixed

- Continuous integration now installs the test dependencies and runs on
  Linux, macOS, and Windows.

## [0.1.0] - 2026-10-22

Initial release: `grab` for one-link downloads and `grab-web` for the local
web page, both built on yt-dlp.
