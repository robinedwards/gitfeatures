"""`git cleanup` deleting local branches that are merged or gone from origin."""

import pytest
from conftest import git

from gitfeatures import core


@pytest.fixture
def branches(repo_with_origin, tmp_path):
    """
    Local branches in every state git cleanup cares about, with main checked out in the repo.
    Returns the names that should be deleted.
    """

    def branch(name, start="main", merge_into=None, delete_on_origin=False):
        git("checkout", "-q", "-b", name, start, cwd=repo_with_origin)
        git("commit", "-q", "--allow-empty", "-m", name, cwd=repo_with_origin)
        git("push", "-q", "-u", "origin", name, cwd=repo_with_origin)
        if merge_into:
            git("push", "-q", "origin", f"{name}:{merge_into}", cwd=repo_with_origin)
        if delete_on_origin:  # as GitHub does after a squash merge
            git("update-ref", "-d", f"refs/heads/{name}", cwd=tmp_path / "origin.git")
        git("checkout", "-q", "main", cwd=repo_with_origin)

    git("push", "-q", "origin", "main:release_x", cwd=repo_with_origin)
    git("fetch", "-q", "origin", cwd=repo_with_origin)
    branch("merged", merge_into="main")
    branch("squashed", delete_on_origin=True)
    branch("unmerged")
    branch("on_release", start="origin/release_x", merge_into="release_x")
    git("config", "branch.on_release.gitfeaturesBase", "release_x", cwd=repo_with_origin)
    branch("in_worktree", start="origin/main", merge_into="main")
    git("worktree", "add", "-q", str(tmp_path / "worktree"), "in_worktree", cwd=repo_with_origin)
    return {"merged", "squashed", "on_release"}


def local_branches(repo_path):
    return set(git("for-each-ref", "--format=%(refname:short)", "refs/heads", cwd=repo_path).split())


def test_deletes_merged_and_gone_branches_only(repo_with_origin, branches, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda: "y")

    core.cleanup([])

    assert local_branches(repo_with_origin) == {"main", "unmerged", "in_worktree"}
    out = capsys.readouterr().out
    assert "merged into origin/release_x" in out and "deleted on origin" in out


def test_dry_run_lists_without_deleting(repo_with_origin, branches, capsys):
    before = local_branches(repo_with_origin)

    core.cleanup(["--dry-run"])

    assert local_branches(repo_with_origin) == before
    out = capsys.readouterr().out
    assert all(name in out for name in branches)
    assert "unmerged" not in out and "in_worktree" not in out
