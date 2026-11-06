import os
import subprocess

import pytest

from gitfeatures import core


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """
    Keep every test away from the developer's own git config and GITFEATURES_* environment, and reset
    the module's settings to their defaults afterwards.
    """
    for name in list(os.environ):
        if name.startswith("GITFEATURES_") or name in ("CONSOLEONLY", "LINEAR_API_KEY", "LINEAR_TOKEN"):
            monkeypatch.delenv(name)
    gitconfig = tmp_path / "gitconfig"
    gitconfig.write_text("[user]\n\tname = Test\n\temail = test@example.com\n[init]\n\tdefaultBranch = main\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    # Stop git from finding a repo above tmp_path, e.g. when the temp dir is inside a checkout.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    core.load_settings()
    yield
    monkeypatch.undo()
    core.load_settings()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A git repo with one commit on main, as the current directory."""
    path = tmp_path / "repo"
    path.mkdir()
    git("init", "-q", cwd=path)
    git("commit", "-q", "--allow-empty", "-m", "init", cwd=path)
    monkeypatch.chdir(path)
    return path


@pytest.fixture
def repo_with_origin(repo, tmp_path):
    """The repo fixture, with a local bare repo as origin and main pushed to it."""
    origin = tmp_path / "origin.git"
    git("init", "-q", "--bare", str(origin))
    git("remote", "add", "origin", str(origin), cwd=repo)
    git("push", "-q", "-u", "origin", "main", cwd=repo)
    return repo


def write_config(repo_path, text):
    (repo_path / core.CONFIG_FILENAME).write_text(text)
