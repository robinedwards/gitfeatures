# Contributing to gitfeatures

## Development setup

You need Python 3.10 or newer and git.

```bash
git clone https://github.com/robinedwards/gitfeatures.git
cd gitfeatures
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
pre-commit install
```

`pip install -e .` puts the `git feature`, `git pullrequest`, `git changelog` and other commands on
your `PATH`, running your working copy.

## Running the tests

```bash
pytest
```

The tests in `tests/` create throwaway git repos in a temp directory, with a local bare repo standing
in for `origin`, so they need no network access and never touch your repos. A fixture in
`tests/conftest.py` clears `GITFEATURES_*` and the other gitfeatures environment variables and points
git at an empty global config, so your own setup cannot change the results.

GitHub Actions runs the tests on every pull request on Python 3.10 to 3.14
(`.github/workflows/tests.yml`).

## Code style

pre-commit runs black (line length 119), isort, flake8, yamllint and an RST linter for `README.rst`.
Run them on your changes before pushing:

```bash
pre-commit run --files <changed files>
```

## Adding a setting

Settings are declared once, in `SETTINGS` in `gitfeatures/core.py`. Each entry gives the module
attribute, the environment variable, the `.gitfeatures` key and the default:

```python
("ticket_prefix", "GITFEATURES_TICKET_PREFIX", "gitfeatures.ticketPrefix", ""),
```

`load_settings()` resolves each one in the order environment variable, `.gitfeatures`, default, and
sets the module attribute, so code reads it as a global (`ticket_prefix`). To add one:

1. Add an entry to `SETTINGS`. For a boolean, also add its attribute to `BOOLEAN_SETTINGS`.
2. Add a placeholder for the attribute next to the others below `SETTINGS`, so flake8 knows the name.
3. Document it in the Settings section of `README.rst`.
4. Add a test to `tests/test_settings.py`, and update `test_defaults_without_env_or_file` and
   `test_reads_every_key_from_gitfeatures_file`.
5. Add a line under `## [Unreleased]` in `CHANGELOG.md`.

Secrets, such as tokens, are never settings. Read them from the environment only, so nobody is tempted
to commit them in `.gitfeatures`.

Every command calls `load_repo_settings()` before it does anything else, so new commands should too.

## Pull requests

- Branch from `master` and open the pull request against `master`. This repo's `.gitfeatures` sets
  that, so `git feature new` and `git pullrequest` do the right thing here.
- Add a line to `CHANGELOG.md` under `## [Unreleased]` for anything users will notice.
- Keep `README.rst` in step with behaviour: it is the user documentation and the PyPI description.
