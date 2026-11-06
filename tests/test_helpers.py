import pytest

from gitfeatures import core


@pytest.mark.parametrize(
    "url, expected",
    [
        ("git@github.com:owner/repo.git", "owner/repo"),
        ("git@github.com:owner/repo.git\n", "owner/repo"),
        ("https://github.com/owner/repo.git", "owner/repo"),
        ("https://github.com/owner/repo", "owner/repo"),
        ("ssh://git@github.com/owner/repo.git", "owner/repo"),
        ("", ""),
    ],
)
def test_repo_full_name_from_origin_url(url, expected):
    assert core._get_repo_full_name_from_origin_url(url) == expected


def test_branch_name_without_ticket():
    assert core._get_branch_name("feature", "my_change") == "feature_my_change"


def test_branch_name_with_ticket_and_prefix(monkeypatch):
    monkeypatch.setenv("GITFEATURES_TICKET_PREFIX", "ENG-")
    monkeypatch.setenv("GITFEATURES_TICKET_SEPERATOR", "-")
    core.load_settings()

    assert core._get_branch_name("feature", "my_change", "123") == "feature_ENG-123-my_change"
    assert core._get_branch_name("feature", "my_change", "ENG-123") == "feature_ENG-123-my_change"


@pytest.mark.parametrize(
    "branch, path",
    [
        ("feature/ENG-1-thing", "changelog/ENG-1-thing.md"),
        ("feature_thing", "changelog/feature_thing.md"),
    ],
)
def test_changelog_path_for_branch(branch, path):
    assert core._get_changelog_path_for_branch(branch) == path


@pytest.mark.parametrize(
    "identifier, prefix, expected",
    [
        ("ENG-123", "", ("ENG", 123)),
        ("eng-7", "", ("ENG", 7)),
        ("123", "ENG-", ("ENG", 123)),
        ("123", "", None),
        ("", "", None),
        ("ENG-abc", "", None),
    ],
)
def test_extract_linear_team_and_number(monkeypatch, identifier, prefix, expected):
    monkeypatch.setenv("GITFEATURES_TICKET_PREFIX", prefix)
    core.load_settings()

    assert core._extract_linear_team_and_number(identifier) == expected


def test_name_has_embedded_ticket(monkeypatch):
    monkeypatch.setenv("GITFEATURES_TICKET_PREFIX", "ENG-")
    monkeypatch.setenv("GITFEATURES_TICKET_SEPERATOR", "-")
    core.load_settings()

    assert core._name_has_embedded_ticket("feature/ENG-12-thing", "feature")
    assert not core._name_has_embedded_ticket("feature/thing", "feature")
    assert not core._name_has_embedded_ticket("hotfix/ENG-12-thing", "feature")
