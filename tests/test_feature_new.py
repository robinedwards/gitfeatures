"""End-to-end `git feature new` against a local bare origin."""

import pytest
from conftest import git, write_config

from gitfeatures import core


def test_feature_new_creates_and_pushes_branch(repo_with_origin):
    core.run("feature", ["new", "my_change"])

    assert git("branch", "--show-current", cwd=repo_with_origin) == "feature_my_change"
    assert "origin/feature_my_change" in git("branch", "-r", cwd=repo_with_origin)
    assert not (repo_with_origin / "changelog").exists()


def test_feature_new_writes_changelog_from_configured_template(repo_with_origin):
    (repo_with_origin / ".github").mkdir()
    (repo_with_origin / ".github" / "changelog.md").write_text("# {{ branch }}\n\n## Rollout\n")
    write_config(
        repo_with_origin,
        "[gitfeatures]\n\tticketPrefix = ENG-\n\tticketSeparator = -\n"
        "[changelog]\n\tenabled = true\n\ttemplate = .github/changelog.md\n",
    )

    core.run("feature", ["new", "feature/ENG-42-my-change"])

    assert git("branch", "--show-current", cwd=repo_with_origin) == "feature/ENG-42-my-change"
    changelog = repo_with_origin / "changelog" / "ENG-42-my-change.md"
    assert changelog.read_text() == "# feature/ENG-42-my-change\n\n## Rollout"


def test_feature_new_uses_branch_separator_from_file(repo_with_origin):
    write_config(repo_with_origin, "[gitfeatures]\n\tbranchSeparator = -\n")

    core.run("feature", ["new", "my_change"])

    assert git("branch", "--show-current", cwd=repo_with_origin) == "feature-my_change"


# Starting from a detached HEAD, as in `git worktree add --detach <path> origin/main`.


def recorded_base(repo, branch):
    return git("config", "--get", f"branch.{branch}.{core.BASE_CONFIG_KEY}", cwd=repo)


def detach_off_main(repo):
    """Detach HEAD at a commit that is on neither main nor origin/main."""
    git("checkout", "-q", "--detach", "main", cwd=repo)
    git("commit", "-q", "--allow-empty", "-m", "ahead of main", cwd=repo)


def no_input():
    raise EOFError


def test_detached_at_master_tip_records_master_without_asking(repo_with_origin, monkeypatch):
    git("checkout", "-q", "--detach", "origin/main", cwd=repo_with_origin)
    monkeypatch.setattr("builtins.input", no_input)

    core.run("feature", ["new", "my_change"])

    assert git("branch", "--show-current", cwd=repo_with_origin) == "feature_my_change"
    assert recorded_base(repo_with_origin, "feature_my_change") == "main"


def test_detached_elsewhere_asks_for_the_base(repo_with_origin, monkeypatch):
    git("push", "-q", "origin", "main:release_x", cwd=repo_with_origin)
    detach_off_main(repo_with_origin)
    answers = iter(["y", "release_x"])  # yes to "not on main", then the base
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    core.run("feature", ["new", "my_change"])

    assert recorded_base(repo_with_origin, "feature_my_change") == "release_x"


def test_detached_elsewhere_rejects_a_base_not_on_origin(repo_with_origin, monkeypatch):
    detach_off_main(repo_with_origin)
    answers = iter(["y", "nope"])
    monkeypatch.setattr("builtins.input", lambda: next(answers))

    with pytest.raises(SystemExit, match="nope .* is not on origin"):
        core.run("feature", ["new", "my_change"])
    assert "feature_my_change" not in git("branch", "--list", cwd=repo_with_origin)


def test_detached_elsewhere_without_an_answer_exits_before_creating_the_branch(repo_with_origin, monkeypatch):
    detach_off_main(repo_with_origin)
    answers = iter(["y"])  # as in `echo y | git feature new`

    def answer():
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr("builtins.input", answer)

    with pytest.raises(SystemExit, match="--base <branch>"):
        core.run("feature", ["new", "my_change"])
    assert "feature_my_change" not in git("branch", "--list", cwd=repo_with_origin)


def test_base_option_records_the_base_without_asking(repo_with_origin, monkeypatch):
    git("push", "-q", "origin", "main:release_x", cwd=repo_with_origin)
    detach_off_main(repo_with_origin)
    monkeypatch.setattr("builtins.input", no_input)

    core.run("feature", ["new", "my_change", "--base", "release_x"])

    assert recorded_base(repo_with_origin, "feature_my_change") == "release_x"
