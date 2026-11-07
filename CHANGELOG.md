# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project adheres loosely to Semantic Versioning.

## [Unreleased]

### Added
- `git cleanup` deletes local branches that are merged into their base branch on origin or whose upstream has been deleted on origin, keeping the base branch and anything checked out in a worktree. It lists them and asks first; `--dry-run` only lists, `--yes` skips the question.
- CI now also runs pre-commit on every file, runs the tests on macOS (Python 3.10 and 3.14), and builds the package and runs the commands from the installed wheel. The workflow token is read-only, and Dependabot keeps the actions up to date.
- CodeQL analysis of the Python code and the workflows, with the `security-and-quality` queries, on pull requests, pushes to `master` and weekly.

### Fixed
- `git feature new` (and `git release new` and the like) records a base branch when started from a detached HEAD, e.g. in a worktree made with `git worktree add --detach <path> origin/main`. At the tip of the base branch it records that without asking; elsewhere it asks which branch, and exits asking for `--base` when there's no answer on stdin. `git feature new` takes `--base <branch>` for scripts. Previously nothing was recorded and `git pullrequest` had to ask.
- `git pullrequest` no longer gives up silently when `GITHUB_TOKEN` and `GH_TOKEN` are unset: it uses the GitHub CLI's token (`gh auth token`) if you're logged in, and otherwise says the pull request wasn't created and prints its URL as well as opening it. A GitHub API error is now printed rather than hidden behind `GITFEATURES_DEBUG`.
- Running out of answers on stdin (e.g. `printf 'y\n' | git pullrequest` when it asks twice) now counts as "no" instead of crashing with `EOFError`.

### Breaking
- Default base branch changed from `master` to `main`. You can override via `GITFEATURES_MASTER_BRANCH`.
- Dropped Python 2 support and removed the `six` dependency. Python 3.10+ is now required (3.8 and 3.9 are end-of-life).

### Added
- Per-repository settings in a committed `.gitfeatures` file (git config format). Every `GITFEATURES_*` environment variable has a matching key; environment variables still work and take precedence, with a notice when they override a value from the file.
- `changelog.template` setting for the changelog template, and `git changelog --init-template [--out <path>] [--force]` to copy the bundled default into a repo for editing and record it in `.gitfeatures`.
- A pytest suite (`tests/`) covering settings, the changelog template, `--init-template`, `git feature new` and `git pullrequest --dry-run`, run by GitHub Actions on Python 3.10 to 3.14.
- Documentation: requirements, a quick start, a migration guide from environment variables to `.gitfeatures`, troubleshooting for every message gitfeatures prints, a full `git changelog` and `git releasecandidate` reference, the template variables, and `CONTRIBUTING.md`.
- Console entry points for all commands via `console_scripts` so `git feature`, `git hotfix`, etc. work when installed.
- `pyproject.toml` with modern build system metadata.
- Comprehensive README with full command and environment variable documentation.

### Changed
- `git feature finish` no longer stops when origin has already deleted the branch (for example GitHub's automatic delete after a merge): it deletes the local branch and the stale `origin/<branch>`.
- `git feature finish` checks the branch is merged before leaving it, then switches to the base branch, or detaches at `origin/<base>` when another worktree has the base branch checked out, instead of always checking out `masterBranch` first. It works in git worktrees and takes `--base <branch>`.
- Each branch now has its own base branch: the branch it was created from, kept in `branch.<name>.gitfeaturesBase`. `git feature new` and `git release`/`stable`/`hotfix new` record it, `git pullrequest` updates the branch from it and opens the PR against it, and `git feature finish` checks the branch is merged into it. For branches made outside gitfeatures, `git pullrequest` reads the start point from git's reflog, or asks; `git pullrequest --base <branch>` sets it. Previously every branch was assumed to come from `gitfeatures.masterBranch`.
- `git pullrequest` brings a branch that is behind up to date by fetching the base branch and merging `origin/<base>` into it (or rebasing onto it) in place, instead of checking out and pulling the base branch first. It now works in a git worktree while the base branch is checked out in another worktree.
- `GITFEATURES_REQUIRE_TICKETID` now accepts `1`, `yes` and `on` as well as `true`, like the other boolean settings.
- `GITFEATURES_TICKET_SEPERATOR` now defaults to the value of `GITFEATURES_BRANCH_SEPERATOR` (previously could be `None`).
- Updated README install instructions to use HTTPS and editable installs.
- Updated script shebangs to `python3` for local direct invocation.

### Fixed
- The README described `git hotfix` as working like `git feature`. It creates date-stamped branches like `git release`, and the README now says so.
- A changelog template path that is set but missing is now reported instead of silently falling back to the bundled default.
- Rendering a changelog no longer exits in a repo without an `origin` remote.
- Corrected a runtime error in pull request flow (replaced `raise ()` with a proper re-raise).

### Removed
- `six` from `install_requires`.
- Self-referential tarball in `requirements-dev.txt`.

[Unreleased]: https://github.com/robinedwards/gitfeatures/compare/v0.1.11...HEAD
