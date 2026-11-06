# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres loosely to Semantic Versioning.

## [Unreleased]

### Breaking
- Default base branch changed from `master` to `main`. You can override via `GITFEATURES_MASTER_BRANCH`.
- Dropped Python 2 support and removed the `six` dependency. Python 3.10+ is now required (3.8 and 3.9 are end-of-life).

### Added
- Per-repository settings in a committed `.gitfeatures` file (git config format). Every `GITFEATURES_*` environment variable has a matching key; environment variables still work and take precedence, with a notice when they override a value from the file.
- `changelog.template` setting for the changelog template, and `git changelog --init-template [--out <path>] [--force]` to copy the bundled default into a repo for editing and record it in `.gitfeatures`.
- A pytest suite (`tests/`) covering settings, the changelog template, `--init-template`, `git feature new` and `git pullrequest --dry-run`, run by GitHub Actions on Python 3.10 to 3.14.
- Console entry points for all commands via `console_scripts` so `git feature`, `git hotfix`, etc. work when installed.
- `pyproject.toml` with modern build system metadata.
- Comprehensive README with full command and environment variable documentation.

### Changed
- `GITFEATURES_REQUIRE_TICKETID` now accepts `1`, `yes` and `on` as well as `true`, like the other boolean settings.
- `GITFEATURES_TICKET_SEPERATOR` now defaults to the value of `GITFEATURES_BRANCH_SEPERATOR` (previously could be `None`).
- Updated README install instructions to use HTTPS and editable installs.
- Updated script shebangs to `python3` for local direct invocation.

### Fixed
- A changelog template path that is set but missing is now reported instead of silently falling back to the bundled default.
- Rendering a changelog no longer exits in a repo without an `origin` remote.
- Corrected a runtime error in pull request flow (replaced `raise ()` with a proper re-raise).

### Removed
- `six` from `install_requires`.
- Self-referential tarball in `requirements-dev.txt`.

[Unreleased]: https://github.com/robinedwards/gitfeatures/compare/v0.1.11...HEAD
