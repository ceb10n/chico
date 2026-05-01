# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `chico list` command to display all configured sources and providers (#21)
- Per-source resource breakdown in `chico status` output (#22)

### Changed
- `.kiro/` directory double-nesting fix: explicit `provider.path` is now used as-is, without appending `.kiro/` suffix (#18)

### Refactored
- State persistence now uses `ResourceRecord` and `LastRunRecord` TypedDicts for type-safe schema definitions (#25)

## [1.1.0b1] - 2026-04-29

### Added
- Project-level Kiro provider resolves `.kiro/` directory from the current working directory instead of a configured absolute path (#12)
- `--source` flag on `plan`, `apply`, `sync`, `diff`, and `schedule` commands to filter by source (#10)

## [1.0.1] - 2026-04-25

### Fixed
- Logo URL changed to absolute path so it renders correctly on PyPI (#4)

### Docs
- Full option descriptions added to `chico init` CLI reference (#6)
- All CLI references updated from `chico` to `chico-ai` (#8)

## [1.0.0] - 2026-04-24

### Added
- Initial release: `init`, `plan`, `apply`, `diff`, `status`, `sync`, and `schedule` commands
- GitHub source provider
- Kiro provider (global and project levels)
- State management with `~/.chico/state.json`
- Structured JSON logging with rotation to `~/.chico/chico.log`

[Unreleased]: https://github.com/ceb10n/chico/compare/v1.1.0b1...HEAD
[1.1.0b1]: https://github.com/ceb10n/chico/compare/v1.0.1...v1.1.0b1
[1.0.1]: https://github.com/ceb10n/chico/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/ceb10n/chico/releases/tag/v1.0.0
