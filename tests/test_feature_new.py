"""End-to-end `git feature new` against a local bare origin."""

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
