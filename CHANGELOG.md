# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres loosely to Semantic Versioning.

## [Unreleased]

### Breaking
- Default base branch changed from `master` to `main`. You can override via `GITFEATURES_MASTER_BRANCH`.
- Dropped Python 2 support and removed the `six` dependency. Python 3.8+ is now required.

### Added
- Console entry points for all commands via `console_scripts` so `git feature`, `git hotfix`, etc. work when installed.
- `pyproject.toml` with modern build system metadata.
- Comprehensive README with full command and environment variable documentation.

### Changed
- `GITFEATURES_TICKET_SEPERATOR` now defaults to the value of `GITFEATURES_BRANCH_SEPERATOR` (previously could be `None`).
- Updated README install instructions to use HTTPS and editable installs.
- Updated script shebangs to `python3` for local direct invocation.

### Fixed
- Corrected a runtime error in pull request flow (replaced `raise ()` with a proper re-raise).

### Removed
- `six` from `install_requires`.
- Self-referential tarball in `requirements-dev.txt`.

[Unreleased]: https://github.com/robinedwards/gitfeatures/compare/v0.1.11...HEAD

