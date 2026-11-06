import pytest
from conftest import git, write_config

from gitfeatures import core


def test_defaults_without_env_or_file(repo):
    settings = core.load_repo_settings()

    assert settings == {
        "repo": "github",
        "master_branch": "main",
        "merge_strategy": "merge",
        "fork_pr_strategy": "",
        "branch_seperator": "_",
        "ticket_seperator": "_",
        "ticket_prefix": "",
        "require_ticket_id": False,
        "debug_enabled": False,
        "changelog_enabled": False,
        "changelog_template_path": "",
    }
    assert set(core.setting_sources.values()) == {"default"}


def test_reads_every_key_from_gitfeatures_file(repo):
    write_config(
        repo,
        "[gitfeatures]\n"
        "\trepo = bitbucket\n"
        "\tmasterBranch = develop\n"
        "\tstrategy = rebase\n"
        "\tforkPrStrategy = private\n"
        "\tbranchSeparator = /\n"
        "\tticketSeparator = -\n"
        "\tticketPrefix = ENG-\n"
        "\trequireTicketId = true\n"
        "\tdebug = on\n"
        "[changelog]\n"
        "\tenabled = yes\n"
        "\ttemplate = .github/changelog.md\n",
    )

    settings = core.load_repo_settings()

    assert settings == {
        "repo": "bitbucket",
        "master_branch": "develop",
        "merge_strategy": "rebase",
        "fork_pr_strategy": "private",
        "branch_seperator": "/",
        "ticket_seperator": "-",
        "ticket_prefix": "ENG-",
        "require_ticket_id": True,
        "debug_enabled": True,
        "changelog_enabled": True,
        "changelog_template_path": ".github/changelog.md",
    }
    assert core.master_branch == "develop"
    assert core.setting_sources["master_branch"] == f"gitfeatures.masterBranch in {repo / '.gitfeatures'}"


def test_keys_are_case_insensitive_and_bare_keys_are_true(repo):
    write_config(repo, "[GitFeatures]\n\tMASTERBRANCH = trunk\n\trequireticketid\n")

    settings = core.load_repo_settings()

    assert settings["master_branch"] == "trunk"
    assert settings["require_ticket_id"] is True


def test_file_is_found_from_a_subdirectory(repo, monkeypatch):
    write_config(repo, "[gitfeatures]\n\tmasterBranch = develop\n")
    (repo / "sub").mkdir()
    monkeypatch.chdir(repo / "sub")

    assert core.load_repo_settings()["master_branch"] == "develop"


def test_ticket_separator_defaults_to_branch_separator_from_file(repo):
    write_config(repo, "[gitfeatures]\n\tbranchSeparator = -\n")

    assert core.load_repo_settings()["ticket_seperator"] == "-"


def test_environment_wins_over_file_with_notice(repo, monkeypatch, capsys):
    write_config(repo, "[gitfeatures]\n\tmasterBranch = develop\n")
    monkeypatch.setenv("GITFEATURES_MASTER_BRANCH", "release")

    settings = core.load_repo_settings()

    assert settings["master_branch"] == "release"
    assert core.setting_sources["master_branch"] == "GITFEATURES_MASTER_BRANCH"
    err = capsys.readouterr().err
    assert "GITFEATURES_MASTER_BRANCH='release' overrides gitfeatures.masterBranch = 'develop'" in err


def test_environment_without_file_value_gives_no_notice(repo, monkeypatch, capsys):
    monkeypatch.setenv("GITFEATURES_TICKET_PREFIX", "ENG-")

    assert core.load_repo_settings()["ticket_prefix"] == "ENG-"
    assert capsys.readouterr().err == ""


def test_equal_booleans_spelled_differently_give_no_notice(repo, monkeypatch, capsys):
    write_config(repo, "[changelog]\n\tenabled = true\n")
    monkeypatch.setenv("GITFEATURES_CHANGELOG_ENABLED", "1")

    assert core.load_repo_settings()["changelog_enabled"] is True
    assert capsys.readouterr().err == ""


def test_empty_environment_variable_still_overrides(repo, monkeypatch):
    write_config(repo, "[gitfeatures]\n\tticketPrefix = ENG-\n")
    monkeypatch.setenv("GITFEATURES_TICKET_PREFIX", "")

    assert core.load_repo_settings()["ticket_prefix"] == ""


@pytest.mark.parametrize(
    "value, expected",
    [("true", True), ("1", True), ("yes", True), ("on", True), ("false", False), ("no", False), ("", False)],
)
def test_boolean_spellings(repo, value, expected):
    write_config(repo, f"[changelog]\n\tenabled = {value}\n")

    assert core.load_repo_settings()["changelog_enabled"] is expected


def test_malformed_file_exits_with_gits_error(repo):
    write_config(repo, "[gitfeatures\n")

    with pytest.raises(SystemExit) as excinfo:
        core.load_repo_settings()

    assert "unable to read" in str(excinfo.value)
    assert "bad config line 1" in str(excinfo.value)


def test_outside_a_repo_uses_environment_and_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITFEATURES_MASTER_BRANCH", "develop")

    assert core._repo_config_path() is None
    assert core.load_repo_settings()["master_branch"] == "develop"


def test_import_does_not_read_a_file(repo):
    write_config(repo, "[gitfeatures]\n\tmasterBranch = develop\n")

    assert core.load_settings()["master_branch"] == "main"


def test_require_ticket_id_from_file_is_enforced(repo):
    write_config(repo, "[gitfeatures]\n\trequireTicketId = yes\n")

    with pytest.raises(SystemExit) as excinfo:
        core.run("feature", ["new", "my_change"])

    assert str(excinfo.value) == "Usage: git feature new <feature_name> <ticket_id>"


def test_pullrequest_refuses_on_base_branch_from_file(repo_with_origin):
    git("switch", "-q", "-c", "trunk", cwd=repo_with_origin)
    write_config(repo_with_origin, "[gitfeatures]\n\tmasterBranch = trunk\n")

    with pytest.raises(SystemExit) as excinfo:
        core.pullrequest(["--dry-run"])

    assert "can't issue pull requests on trunk" in str(excinfo.value)


def test_pullrequest_dry_run_compares_against_base_branch_from_file(repo_with_origin, capsys):
    git("push", "-q", "origin", "main:trunk", cwd=repo_with_origin)
    git("switch", "-q", "-c", "feature_x", cwd=repo_with_origin)
    git("push", "-q", "-u", "origin", "feature_x", cwd=repo_with_origin)
    write_config(repo_with_origin, "[gitfeatures]\n\tmasterBranch = trunk\n\tforkPrStrategy = private\n")

    core.pullrequest(["--dry-run"])

    assert capsys.readouterr().out.strip().endswith("/compare/trunk...feature_x")
