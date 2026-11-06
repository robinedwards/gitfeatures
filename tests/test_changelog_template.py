import pytest
from conftest import write_config

from gitfeatures import core


def bundled_template():
    with open(core.DEFAULT_CHANGELOG_TEMPLATE, encoding="utf-8") as fh:
        return fh.read()


def resolve():
    core.load_repo_settings()
    return core._changelog_template_file()


def test_bundled_default_when_nothing_configured(repo):
    assert resolve() == core.DEFAULT_CHANGELOG_TEMPLATE


def test_repo_root_changelog_template_is_still_picked_up(repo):
    (repo / "changelog-template.md").write_text("legacy")

    assert resolve() == str(repo / "changelog-template.md")


def test_configured_relative_path_wins_over_repo_root_file(repo):
    (repo / "changelog-template.md").write_text("legacy")
    (repo / ".github").mkdir()
    (repo / ".github" / "changelog.md").write_text("configured")
    write_config(repo, "[changelog]\n\ttemplate = .github/changelog.md\n")

    assert resolve() == str(repo / ".github" / "changelog.md")


def test_configured_absolute_path(repo, tmp_path):
    template = tmp_path / "shared-template.md"
    template.write_text("shared")
    write_config(repo, f"[changelog]\n\ttemplate = {template}\n")

    assert resolve() == str(template)


def test_environment_variable_still_sets_the_template(repo, monkeypatch):
    (repo / "env-template.md").write_text("from env")
    monkeypatch.setenv("GITFEATURES_CHANGELOG_TEMPLATE", "env-template.md")

    assert resolve() == str(repo / "env-template.md")


def test_missing_configured_template_is_reported_and_falls_back_to_default(repo, capsys):
    (repo / "changelog-template.md").write_text("legacy")
    write_config(repo, "[changelog]\n\ttemplate = gone.md\n")

    assert resolve() == core.DEFAULT_CHANGELOG_TEMPLATE
    err = capsys.readouterr().err
    assert f"changelog template {repo / 'gone.md'}" in err
    assert "set by changelog.template in" in err


def test_init_template_copies_default_and_configures_repo(repo, monkeypatch, capsys):
    (repo / "sub").mkdir()
    monkeypatch.chdir(repo / "sub")

    core.preview_changelog(["--init-template"])

    assert (repo / "changelog-template.md").read_text() == bundled_template()
    settings = core.load_repo_settings()
    assert settings["changelog_template_path"] == "changelog-template.md"
    assert settings["changelog_enabled"] is True
    assert "Edit the template, then commit it and .gitfeatures." in capsys.readouterr().out


def test_init_template_to_custom_path(repo):
    core.preview_changelog(["--init-template", "--out", ".github/changelog-template.md"])

    assert (repo / ".github" / "changelog-template.md").read_text() == bundled_template()
    assert core.load_repo_settings()["changelog_template_path"] == ".github/changelog-template.md"


def test_init_template_writes_to_already_configured_path(repo):
    write_config(repo, "[changelog]\n\ttemplate = docs/changelog.md\n")

    core.preview_changelog(["--init-template"])

    assert (repo / "docs" / "changelog.md").read_text() == bundled_template()


def test_init_template_keeps_existing_enabled_setting(repo):
    write_config(repo, "[changelog]\n\tenabled = false\n")

    core.preview_changelog(["--init-template"])

    assert core.load_repo_settings()["changelog_enabled"] is False


def test_init_template_refuses_to_overwrite_without_force(repo):
    (repo / "changelog-template.md").write_text("mine")

    with pytest.raises(SystemExit) as excinfo:
        core.preview_changelog(["--init-template"])

    assert "already exists. Use --force" in str(excinfo.value)
    assert (repo / "changelog-template.md").read_text() == "mine"


def test_init_template_force_overwrites(repo):
    (repo / "changelog-template.md").write_text("mine")

    core.preview_changelog(["--init-template", "--force"])

    assert (repo / "changelog-template.md").read_text() == bundled_template()


def test_init_template_rejects_preview_flags(repo):
    with pytest.raises(SystemExit) as excinfo:
        core.preview_changelog(["--init-template", "--write"])

    assert str(excinfo.value) == core.CHANGELOG_USAGE


def test_preview_renders_edited_template(repo, capsys):
    core.preview_changelog(["--init-template"])
    template = repo / "changelog-template.md"
    template.write_text(template.read_text().replace("## Testing", "## How to test"))
    capsys.readouterr()

    core.preview_changelog(["--branch", "feature/my-change"])

    out = capsys.readouterr().out
    assert out.startswith("# feature/my-change\n")
    assert "## How to test" in out


def test_preview_works_without_origin_remote(repo, capsys):
    core.preview_changelog(["--branch", "feature/my-change"])

    assert "## Changes" in capsys.readouterr().out


def test_preview_write_defaults_to_changelog_directory(repo, capsys):
    core.preview_changelog(["--branch", "feature/my-change", "--write"])

    assert capsys.readouterr().out.strip() == "changelog/my-change.md"
    assert (repo / "changelog" / "my-change.md").read_text().startswith("# feature/my-change")


def test_bundled_default_renders_without_an_issue():
    context = {"branch": "feature/x", "title": "", "background": "", "changes": "- ", "testing": "- "}
    context.update({"linear": {}, "issue": {}})

    rendered = core._render_changelog_template(bundled_template(), context)

    for heading in ("# feature/x", "## Purpose", "## Changes", "## Testing"):
        assert heading in rendered
    assert "## Background" not in rendered
    assert "## Links" not in rendered


def test_bundled_default_renders_issue_details():
    issue = {"identifier": "ENG-1", "title": "Do it", "url": "https://linear.app/x/issue/ENG-1"}
    context = {"branch": "feature/x", "title": "Do it", "background": "Because", "changes": "- ", "testing": "- "}
    context.update({"linear": issue, "issue": {"provider": "linear", "url": issue["url"]}})

    rendered = core._render_changelog_template(bundled_template(), context)

    assert "- Identifier: ENG-1" in rendered
    assert "Because" in rendered
    assert "- Linear: https://linear.app/x/issue/ENG-1" in rendered
