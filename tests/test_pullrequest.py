"""`git pullrequest` bringing a branch up to date with origin/<base> from a git worktree."""

import pytest
from conftest import git, write_config

from gitfeatures import core


@pytest.fixture
def behind_in_worktree(repo_with_origin, tmp_path, monkeypatch):
    """
    A feature branch with one commit, checked out in a second worktree while main stays checked out in
    the first, and origin/main one commit ahead of where the feature branched off.
    """
    worktree = tmp_path / "worktree"
    git("worktree", "add", "-q", "-b", "feature_x", str(worktree), "main", cwd=repo_with_origin)
    (worktree / "feature.txt").write_text("feature\n")
    git("add", "feature.txt", cwd=worktree)
    git("commit", "-q", "-m", "feature work", cwd=worktree)
    git("push", "-q", "-u", "origin", "feature_x", cwd=worktree)

    (repo_with_origin / "main.txt").write_text("main\n")
    git("add", "main.txt", cwd=repo_with_origin)
    git("commit", "-q", "-m", "main work", cwd=repo_with_origin)
    git("push", "-q", "origin", "main", cwd=repo_with_origin)

    monkeypatch.chdir(worktree)
    # Yes to updating from origin/main, no to pushing.
    answers = iter(["y", "n"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))
    return worktree


def test_merges_origin_base_without_leaving_the_branch(behind_in_worktree):
    core.pullrequest(["--dry-run"])

    assert git("branch", "--show-current", cwd=behind_in_worktree) == "feature_x"
    git("merge-base", "--is-ancestor", "origin/main", "HEAD", cwd=behind_in_worktree)
    assert git("log", "-1", "--format=%P", cwd=behind_in_worktree).count(" ") == 1  # a merge commit
    assert (behind_in_worktree / "main.txt").exists()


def test_rebases_onto_origin_base_without_leaving_the_branch(behind_in_worktree, repo_with_origin):
    write_config(behind_in_worktree, "[gitfeatures]\n\tstrategy = rebase\n")

    core.pullrequest(["--dry-run"])

    assert git("branch", "--show-current", cwd=behind_in_worktree) == "feature_x"
    assert git("rev-parse", "HEAD~1", cwd=behind_in_worktree) == git("rev-parse", "origin/main", cwd=repo_with_origin)
    assert git("log", "-1", "--format=%s", cwd=behind_in_worktree) == "feature work"


@pytest.mark.parametrize("strategy, finish", [("merge", "git commit"), ("rebase", "git rebase --continue")])
def test_stops_on_conflict_with_instructions(behind_in_worktree, strategy, finish):
    write_config(behind_in_worktree, f"[gitfeatures]\n\tstrategy = {strategy}\n")
    (behind_in_worktree / "main.txt").write_text("feature's version\n")
    git("add", "main.txt", cwd=behind_in_worktree)
    git("commit", "-q", "-m", "conflicting work", cwd=behind_in_worktree)

    with pytest.raises(SystemExit) as exc:
        core.pullrequest(["--dry-run"])

    message = str(exc.value)
    assert "CONFLICT" in message
    assert "git add" in message and finish in message and "git pullrequest" in message


def test_refuses_on_the_base_branch(repo_with_origin):
    with pytest.raises(SystemExit, match="can't issue pull requests on main"):
        core.pullrequest(["--dry-run"])


@pytest.fixture
def release_x(repo_with_origin, tmp_path):
    """A release_x branch on origin, created from main. Returns a function that adds a commit to an origin branch."""
    git("push", "-q", "origin", "main:release_x", cwd=repo_with_origin)
    clone = tmp_path / "clone"
    git("clone", "-q", str(tmp_path / "origin.git"), str(clone))

    def commit_on_origin(branch, filename):
        git("checkout", "-q", "-B", branch, f"origin/{branch}", cwd=clone)
        (clone / filename).write_text(f"{filename}\n")
        git("add", filename, cwd=clone)
        git("commit", "-q", "-m", filename, cwd=clone)
        git("push", "-q", "origin", branch, cwd=clone)

    return commit_on_origin


def answer(monkeypatch, *answers):
    replies = iter(answers)
    monkeypatch.setattr("builtins.input", lambda: next(replies))


def test_branch_from_feature_new_is_updated_from_and_targets_its_own_base(
    repo_with_origin, release_x, monkeypatch, capsys
):
    git("checkout", "-q", "-b", "release_x", "origin/release_x", cwd=repo_with_origin)
    answer(monkeypatch, "y")  # yes, branch from release_x rather than main
    core.run("feature", ["new", "y"])
    assert git("config", "branch.feature_y.gitfeaturesBase", cwd=repo_with_origin) == "release_x"

    release_x("release_x", "release.txt")
    release_x("main", "main.txt")
    answer(monkeypatch, "y", "n")  # update from the base, don't push
    core.pullrequest(["--dry-run"])

    assert (repo_with_origin / "release.txt").exists()
    assert not (repo_with_origin / "main.txt").exists()
    assert "/compare/release_x...feature_y" in capsys.readouterr().out


def test_base_of_a_branch_made_outside_gitfeatures_comes_from_where_git_created_it(
    repo_with_origin, release_x, tmp_path, monkeypatch
):
    worktree = tmp_path / "worktree"
    git("worktree", "add", "-q", "-b", "feature_z", str(worktree), "origin/release_x", cwd=repo_with_origin)
    git("push", "-q", "-u", "origin", "feature_z", cwd=worktree)
    release_x("release_x", "release.txt")
    release_x("main", "main.txt")
    monkeypatch.chdir(worktree)
    answer(monkeypatch, "y", "n")

    core.pullrequest(["--dry-run"])

    assert (worktree / "release.txt").exists()
    assert not (worktree / "main.txt").exists()
    assert git("config", "branch.feature_z.gitfeaturesBase", cwd=worktree) == "release_x"


def test_unknown_base_is_asked_for_and_given_with_base_flag(repo_with_origin, release_x, monkeypatch):
    git("checkout", "-q", "-b", "feature_q", cwd=repo_with_origin)  # git only records "Created from HEAD"
    git("push", "-q", "-u", "origin", "feature_q", cwd=repo_with_origin)
    release_x("release_x", "release.txt")

    answer(monkeypatch, "n")  # no, main is not the base
    with pytest.raises(SystemExit, match="--base"):
        core.pullrequest(["--dry-run"])

    answer(monkeypatch, "y", "n")
    core.pullrequest(["--base", "release_x", "--dry-run"])

    assert (repo_with_origin / "release.txt").exists()
    assert git("config", "branch.feature_q.gitfeaturesBase", cwd=repo_with_origin) == "release_x"


def test_feature_finish_checks_the_branch_is_merged_into_its_own_base(repo_with_origin, release_x, monkeypatch):
    git("checkout", "-q", "-b", "release_x", "origin/release_x", cwd=repo_with_origin)
    answer(monkeypatch, "y")  # yes, branch from release_x rather than main
    core.run("feature", ["new", "y"])
    git("commit", "-q", "--allow-empty", "-m", "feature work", cwd=repo_with_origin)
    git("push", "-q", "origin", "feature_y:release_x", cwd=repo_with_origin)  # merged into release_x only

    core.run("feature", ["finish"])

    assert "feature_y" not in git("branch", "-a", cwd=repo_with_origin)


def test_feature_finish_in_a_worktree_while_the_base_is_checked_out_elsewhere(repo_with_origin, tmp_path, monkeypatch):
    worktree = tmp_path / "worktree"
    git("worktree", "add", "-q", "-b", "feature_w", str(worktree), "main", cwd=repo_with_origin)
    git("commit", "-q", "--allow-empty", "-m", "feature work", cwd=worktree)
    git("push", "-q", "-u", "origin", "feature_w", cwd=worktree)
    git("push", "-q", "origin", "feature_w:main", cwd=worktree)  # merged
    monkeypatch.chdir(worktree)

    core.run("feature", ["finish"])

    assert git("branch", "--show-current", cwd=worktree) == ""  # detached, as main is in the other worktree
    assert git("rev-parse", "HEAD", cwd=worktree) == git("rev-parse", "origin/main", cwd=worktree)
    assert "feature_w" not in git("branch", "-a", cwd=repo_with_origin)


def test_feature_finish_when_origin_already_deleted_the_branch(repo_with_origin):
    git("checkout", "-q", "-b", "feature_d", "main", cwd=repo_with_origin)
    git("commit", "-q", "--allow-empty", "-m", "feature work", cwd=repo_with_origin)
    git("push", "-q", "-u", "origin", "feature_d", cwd=repo_with_origin)
    git("push", "-q", "origin", "feature_d:main", cwd=repo_with_origin)  # merged
    # GitHub deletes the merged branch; the local origin/feature_d is left behind until a prune
    git("update-ref", "-d", "refs/heads/feature_d", cwd=repo_with_origin.parent / "origin.git")

    core.run("feature", ["finish"])

    assert git("branch", "--show-current", cwd=repo_with_origin) == "main"
    assert "feature_d" not in git("branch", "-a", cwd=repo_with_origin)
