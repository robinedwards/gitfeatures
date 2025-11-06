import os
import re
import sys
import datetime
import webbrowser
from subprocess import CalledProcessError, check_output
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Optional, Tuple, Dict, Any
import jinja2  # Airflow uses Jinja2 for templating

master_branch = os.environ.get("GITFEATURES_MASTER_BRANCH", "main")
branch_seperator = os.environ.get("GITFEATURES_BRANCH_SEPERATOR", "_")
ticket_seperator = os.environ.get("GITFEATURES_TICKET_SEPERATOR", branch_seperator)
ticket_prefix = os.environ.get("GITFEATURES_TICKET_PREFIX", "")
repo = os.environ.get("GITFEATURES_REPO", "github")
merge_strategy = os.environ.get("GITFEATURES_STRATEGY", "merge")
fork_pr_strategy = os.environ.get("GITFEATURES_FORK_PR_STRATEGY", "")
require_ticket_id = os.environ.get("GITFEATURES_REQUIRE_TICKETID", "false")


def _debug(message):
    if str(os.environ.get("GITFEATURES_DEBUG", "")).lower() in ("1", "true", "yes", "on"):  # noqa
        print(f"[gitfeatures] {message}")


def _call(args):
    try:
        return check_output(args).decode("utf-8")
    except CalledProcessError:
        sys.exit(__name__ + ": none zero exit status executing: " + " ".join(args))  # noqa


def _get_repo_full_name_from_origin_url(origin_url):
    """
    Extract the 'owner/repo' full name from a git remote URL (ssh or https).
    """
    if not origin_url:
        return ""
    origin_url = origin_url.strip()
    # git@github.com:owner/repo.git
    if origin_url.startswith("git@"):
        try:
            after_colon = origin_url.split(":", 1)[1]
            return after_colon.replace(".git", "").strip()
        except Exception:
            return ""
    # https://github.com/owner/repo.git or http(s) with extra path
    try:
        parsed = urllib.parse.urlparse(origin_url)
        if parsed.netloc:
            path = parsed.path.lstrip("/")
            if path:
                return path.replace(".git", "").strip()
    except Exception:
        pass
    # Fallback: attempt split by ':' like ssh
    if ":" in origin_url:
        return origin_url.split(":", 1)[1].replace(".git", "").strip()
    return origin_url.replace(".git", "").strip()


def _get_changelog_path_for_branch(branch):
    """
    Return the path to the changelog file for a given branch.
    Preserves slashes in branch names as nested directories under 'changelog/'.
    """
    return os.path.join("changelog", f"{branch}.md")


def _read_changelog_body(branch):
    """
    Read the changelog file for the branch if it exists, else return None.
    """
    path = _get_changelog_path_for_branch(branch)
    if os.path.exists(path) and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except Exception as e:
            _debug(f"Failed to read changelog file at {path}: {e}")
    return None


def _get_repo_root() -> str:
    """
    Return the absolute path to the git repository root, falling back to CWD.
    """
    try:
        root = _call(["git", "rev-parse", "--show-toplevel"]).strip()
        return root if root else os.getcwd()
    except Exception:
        return os.getcwd()


def _read_user_story_template() -> Optional[str]:
    """
    Read user-story-template.md (or path from GITFEATURES_STORY_TEMPLATE) from the repo.
    """
    repo_root = _get_repo_root()
    override = os.environ.get("GITFEATURES_STORY_TEMPLATE", "").strip()
    if override:
        path = override if os.path.isabs(override) else os.path.join(repo_root, override)
    else:
        path = os.path.join(repo_root, "user-story-template.md")
    if os.path.exists(path) and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except Exception as e:
            _debug(f"Failed to read user-story-template.md: {e}")
    return None


def _read_changelog_template() -> Optional[str]:
    """
    Read changelog-template.md (or path from GITFEATURES_CHANGELOG_TEMPLATE) from the repo.
    """
    repo_root = _get_repo_root()
    override = os.environ.get("GITFEATURES_CHANGELOG_TEMPLATE", "").strip()
    if override:
        path = override if os.path.isabs(override) else os.path.join(repo_root, override)
    else:
        path = os.path.join(repo_root, "changelog-template.md")
    if os.path.exists(path) and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return fh.read()
        except Exception as e:
            _debug(f"Failed to read changelog-template.md: {e}")
    # Fallback to bundled default template inside the package
    try:
        pkg_dir = os.path.dirname(__file__)
        bundled = os.path.join(pkg_dir, "templates", "changelog-template.md")
        if os.path.exists(bundled) and os.path.isfile(bundled):
            with open(bundled, "r", encoding="utf-8") as fh:
                return fh.read()
    except Exception as e:
        _debug(f"Failed to read bundled changelog template: {e}")
    return None


def _build_changelog_context(branch: str, ticket_identifier: Optional[str], linear_issue: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a Jinja2 context for rendering user-story-template.md.
    """
    # Suggested fields
    title = (linear_issue.get("title") if linear_issue else "") or branch
    background = (linear_issue.get("description") if linear_issue else "") or ""
    repo_origin = ""
    repo_full_name = ""
    try:
        repo_origin = _call(["git", "config", "--get", "remote.origin.url"])
        repo_full_name = _get_repo_full_name_from_origin_url(repo_origin)
    except Exception:
        pass
    # Generic issue payload for potential multiple providers
    issue: Dict[str, Any] = {}
    if linear_issue:
        issue = {
            "provider": "linear",
            "id": linear_issue.get("identifier"),
            "key": linear_issue.get("identifier"),
            "title": linear_issue.get("title"),
            "description": linear_issue.get("description"),
            "url": linear_issue.get("url"),
        }
    context = {
        "branch": branch,
        "ticket": ticket_identifier,
        "repo_origin": repo_origin.strip(),
        "repo_full_name": repo_full_name,
        "linear": linear_issue or {},
        "issue": issue,
        "title": title,
        "background": background,
        "changes": "- ",
        "testing": "- ",
        "now": datetime.datetime.utcnow().isoformat() + "Z",
        "master_branch": master_branch,
    }
    return context


def _render_changelog_template(template_text: str, context: Dict[str, Any]) -> Optional[str]:
    """
    Render the provided template text with Jinja2 using the given context.
    """
    try:
        template = jinja2.Template(template_text, autoescape=False)
        return template.render(**context)
    except Exception as e:
        _debug(f"Jinja2 render failed: {e}")
        return None


""  # Removed seed parsing helpers; templating now handles all initial content


def _extract_linear_team_and_number(identifier: str) -> Optional[Tuple[str, int]]:
    """
    Given an identifier like 'ENG-123', return ('ENG', 123).
    If the configured ticket_prefix is like 'ENG-' and identifier is just '123',
    we attempt to prepend and parse.
    """
    if not identifier:
        return None
    ident = identifier.strip().upper()
    # Normalize: if configured prefix exists and ident is digits-only, attach
    if ticket_prefix and ident.isdigit():
        norm_prefix = ticket_prefix.strip().upper()
        ident = f"{norm_prefix}{ident}"
    # Common pattern TEAM-123
    try:
        if "-" in ident:
            team, num = ident.split("-", 1)
            if team and num.isdigit():
                return team, int(num)
    except Exception:
        return None
    return None


def _fetch_linear_issue(team_key: str, number: int, token: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a Linear issue by team key and issue number using GraphQL.
    Returns a dict with identifier, title, description, url on success; else None.
    """
    endpoint = "https://api.linear.app/graphql"
    query = """
    query Issues($teamKey: String!, $number: Int!) {
      issues(filter: { number: { eq: $number }, team: { key: { eq: $teamKey } } }, first: 1) {
        nodes {
          id
          identifier
          title
          description
          url
        }
      }
    }
    """
    payload = {"query": query, "variables": {"teamKey": team_key, "number": number}}
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "gitfeatures",
    }
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            parsed = json.loads(resp_body)
            nodes = (((parsed or {}).get("data") or {}).get("issues") or {}).get("nodes") or []
            if nodes:
                node = nodes[0]
                return {
                    "identifier": node.get("identifier"),
                    "title": node.get("title"),
                    "description": node.get("description") or "",
                    "url": node.get("url"),
                }
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        _debug(f"Linear API error: {err_body}")
    except Exception as e:
        _debug(f"Linear API exception: {e}")
    return None


# Removed inline initial changelog builder in favor of bundled Jinja2 template


def _create_github_pr_with_token(repo_full_name, head_branch, base_branch, body_text, token):
    """
    Create a GitHub Pull Request using the REST API.
    Returns (success, response_json or error_text).
    """
    api_url = f"https://api.github.com/repos/{repo_full_name}/pulls"
    title = head_branch
    payload = {"title": title, "head": head_branch, "base": base_branch}
    if body_text:
        payload["body"] = body_text
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "gitfeatures",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(api_url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            parsed = json.loads(resp_body)
            return True, parsed
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        return False, err_body
    except Exception as e:
        return False, str(e)


def _get_branch_name(prefix, name, ticket_id=None):
    branch_name = f"{prefix}{branch_seperator}{name}"
    if ticket_id:
        if ticket_prefix:
            if not ticket_id.startswith(ticket_prefix):
                ticket_id = f"{ticket_prefix}{ticket_id}"
        branch_name = f"{prefix}{branch_seperator}{ticket_id}{ticket_seperator}{name}"
    return branch_name


def new_feature(name, prefix, ticket_id=None):
    # Allow alnum, underscore, hyphen, and slash in branch inputs
    name = re.sub(r"[^\w\-/]", "_", name)
    original_branch = _current_branch()
    if original_branch != master_branch:
        print(_current_branch(), master_branch)
        print(
            "You aren't on your main {} branch. Are you sure you wish to create a branch from {}? [y/n]".format(
                master_branch, original_branch
            )
        )  # noqa
        if input().lower() != "y":
            sys.exit("Ok, Exiting")  # noqa

    _call(["git", "remote", "update", "origin"])
    # Support input names like 'feature/eng-123-some-description'
    # If the provided name already starts with '<prefix>/' treat it as a full branch path
    if name.lower().startswith(prefix.lower() + "/"):
        rest = name.split("/", 1)[1]
        parsed_branch = None
        detected_ticket_identifier = None
        # Optionally normalize ticket id using env-provided prefix and separator
        if ticket_seperator and ticket_prefix:
            pattern = re.compile(
                r"^(" + re.escape(ticket_prefix) + r")(\d+)" + re.escape(ticket_seperator) + r"(.*)$",
                re.IGNORECASE,
            )
            m = pattern.match(rest)
            if m:
                number = m.group(2)
                slug = m.group(3)
                normalized_ticket = f"{ticket_prefix}{number}"
                parsed_branch = f"{prefix}/{normalized_ticket}{ticket_seperator}{slug}"
                _debug(
                    f"Detected ticket in input. normalized_ticket={normalized_ticket}, slug={slug}, branch={parsed_branch}"
                )
                detected_ticket_identifier = normalized_ticket
        new_branch = parsed_branch if parsed_branch else name
    else:
        new_branch = _get_branch_name(prefix, name, ticket_id)
        # If a ticket_id was provided, construct the identifier for downstream use
        detected_ticket_identifier = None
        if ticket_id:
            if ticket_prefix and not str(ticket_id).startswith(ticket_prefix):
                detected_ticket_identifier = f"{ticket_prefix}{ticket_id}"
            else:
                detected_ticket_identifier = str(ticket_id)
    _debug(f"Creating new branch: {new_branch}")

    if _branch_exists(new_branch):
        sys.exit(__name__ + ": local or remote branch already exists: " + new_branch)  # noqa

    _call(["git", "checkout", "-b", new_branch])
    _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])
    # Create changelog file for this branch if not present
    try:
        changelog_path = _get_changelog_path_for_branch(new_branch)
        parent_dir = os.path.dirname(changelog_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        if not os.path.exists(changelog_path):
            # Optionally fetch Linear issue to prefill context
            linear_issue = None
            linear_token = os.environ.get("LINEAR_API_KEY") or os.environ.get("LINEAR_TOKEN")
            if linear_token and detected_ticket_identifier:
                parsed = _extract_linear_team_and_number(detected_ticket_identifier)
                if parsed:
                    team_key, number = parsed
                    linear_issue = _fetch_linear_issue(team_key, number, linear_token)
            # Render changelog from dedicated changelog template
            initial_body = ""
            changelog_template = _read_changelog_template()
            if changelog_template:
                context = _build_changelog_context(new_branch, detected_ticket_identifier, linear_issue)
                rendered = _render_changelog_template(changelog_template, context)
                if rendered is not None:
                    initial_body = rendered
            # If no template or render fails, create empty file (no default)
            with open(changelog_path, "w", encoding="utf-8") as fh:
                fh.write(initial_body)
            _debug(f"Created changelog file: {changelog_path}")
    except Exception as e:
        _debug(f"Unable to create changelog file: {e}")


def finish_feature(name, prefix):
    cur_branch = _current_branch()

    if name:
        branch = _get_branch_name(prefix, name)
        if branch == cur_branch:
            _call(["git", "checkout", master_branch])
    elif cur_branch != master_branch:
        branch = cur_branch
        _call(["git", "checkout", master_branch])
    else:
        sys.exit(__name__ + ": please provide a branch name if on {}".format(master_branch))

    _call(["git", "remote", "update", "origin"])

    commits = _call(["git", "log", "--oneline", branch, "^origin/{}".format(master_branch)])
    if commits:
        sys.exit(
            __name__
            + ": "
            + branch
            + " contains commits that are not in {}:\n".format(master_branch)
            + commits
            + "\nraise a pull request and get them merged in."
        )
    else:
        _call(["git", "push", "origin", ":" + branch])
        _call(["git", "branch", "-D", branch])


def _branch_func(branch_type, args):
    if len(args) > 0 and args[0] == "new":
        prefix = ""
        now = datetime.datetime.now()
        date = now.date()
        date_string = date.strftime("%Y%m%d")

        if len(args) == 2:
            prefix = args[1]
        else:
            time = now.time()
            time_string = time.strftime("%H%M%S")
            prefix = time_string

        name = "{}_{}".format(date_string, prefix)
        new_branch = _get_branch_name(branch_type, name)

        _call(["git", "checkout", "-b", new_branch])
        _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])

        branches = _get_branches(branch_type)
        if len(branches) > 3:
            branch = branches[0]
            print(
                f"you have more than 3 {branch_type} branches, shall I delete the eldest one ({branch})? [y/n]"
            )  # noqa
            if input().lower() == "y":
                _call(["git", "push", "origin", "--delete", branch])
                _call(["git", "branch", "-D", branch])
    else:
        # checkout the latest branch
        branches = _get_branches(branch_type)
        if branches:
            branch = branches[-1]
            _call(["git", "checkout", branch])
        else:
            print(f"No {branch_type} branches")


def stable(args):
    return _branch_func("stable", args)


def hotfix(args):
    return _branch_func("hotfix", args)


def release(args):
    return _branch_func("release", args)


def pullrequest(args):
    branch = _current_branch()
    if branch == master_branch:
        sys.exit(__name__ + ": can't issue pull requests on {}".format(master_branch))

    # check its up to date with remote master if not pull
    _call(["git", "remote", "update", "origin"])
    commits = _call(["git", "log", "--oneline", "^" + branch, "origin/{}".format(master_branch)])
    if commits:
        print(
            "Your branch is behind origin/{} so cannot be automatically {}d.".format(master_branch, merge_strategy)
        )  # noqa
        print(commits)
        print(
            "Do you wish to update and {} {} (If conflicts occur, you will be able to fix them)? [y/n]".format(
                merge_strategy, master_branch
            )
        )  # noqa
        if input().lower() == "y":
            _call(["git", "checkout", master_branch])
            _call(["git", "pull"])
            _call(["git", "checkout", branch])
            try:
                print("git {} {}".format(merge_strategy, master_branch))
                output = check_output(["git", merge_strategy, master_branch]).decode("utf-8")
                print(output)
                print("Congratulations, successfully {}d {}".format(merge_strategy, master_branch))
            except CalledProcessError as e:
                if b"CONFLICT" in e.output:
                    err = (
                        e.output.decode()
                        + " \n\nUnlucky! You have work to do. Fix the above conflicts and run git pullrequest again"
                    )  # noqa
                    sys.exit(err)
                else:
                    raise

    # check if there are any unpushed commits
    commits = _call(["git", "log", "--oneline", branch, "^origin/" + branch])
    if commits:
        print("You have unpushed commits:")
        print(commits)
        print("Push commits to origin [y/n]")
        if input().lower() == "y":
            _call(["git", "push", "origin", branch + ":" + branch])

    origin = _call(["git", "config", "--get", "remote.origin.url"])
    print("origin", origin)
    name = _get_repo_full_name_from_origin_url(origin)
    print("name", name)
    print("branch", branch)
    url = _get_pullrequest_url(name, branch)
    if (len(args) > 0 and args[0] == "--dry-run") or os.environ.get("CONSOLEONLY", False):  # noqa
        print(url)
    else:
        # If a GitHub token is present, attempt to create the PR via API
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if repo == "github" and token:
            body = _read_changelog_body(branch)
            ok, resp = _create_github_pr_with_token(name, branch, master_branch, body, token)
            if ok:
                pr_url = resp.get("html_url") or url
                print(f"Created PR: {pr_url}")
                return
            else:
                print("Failed to create PR via API. Falling back to browser flow.")
                _debug(f"GitHub API error: {resp}")
        webbrowser.open_new_tab(url)


def _get_pullrequest_url(name, branch):
    print("pullrequest", name, branch, fork_pr_strategy)
    if repo == "github":
        if fork_pr_strategy == "private":
            url = f"https://github.com/{name}/compare/{master_branch}...{branch}"
        else:
            url = "https://github.com/" + name + "/pull/new/" + branch
    elif repo == "bitbucket":
        url = "https://bitbucket.org/" + name + "/pull-requests/new?t=1&source=" + branch  # noqa
    return url


def _current_branch():
    output = _call(["git", "branch"])
    branch = re.search(r"^\* (.+)$", output, flags=re.M).group(1)
    if not branch:
        sys.exit(__name__ + ": unable to detect current branch")
    else:
        return branch


def _branch_exists(name):
    branch_list = _call(["git", "branch", "-a"])
    return 1 if re.search(r"" + name + "$", branch_list, flags=re.M) else 0


def _get_branches(branch_type):
    _call(["git", "remote", "update", "origin"])
    try:
        pattern = rf"/{branch_type}{branch_seperator}[0-9]{{8}}"
        branch_list = (
            check_output(
                f"git branch -r | grep -E '{pattern}'",
                shell=True,
            )
            .decode("utf-8")
            .strip()
        )
        branch_list = branch_list.split("\n")
        branch_list = list(map(lambda it: it.split("/", 1)[1].strip(), branch_list))

        return branch_list
    except CalledProcessError:
        return []


def _name_has_embedded_ticket(candidate_name, prefix):
    if not (ticket_seperator and ticket_prefix):
        return False
    if not candidate_name.lower().startswith(prefix.lower() + "/"):
        return False
    rest = candidate_name.split("/", 1)[1]
    pattern = re.compile(
        r"^(" + re.escape(ticket_prefix) + r")(\d+)" + re.escape(ticket_seperator) + r"",
        re.IGNORECASE,
    )
    return bool(pattern.match(rest))


def run(prefix, args):
    if len(args) and args[0].lower() == "new":
        allowed_branch_types = ["releasecandidate", "stable", "release", "hotfix"]
        if prefix in allowed_branch_types:
            if len(args) == 2:
                new_feature(args[1], prefix)
            else:
                name = str(datetime.date.today())
                new_feature(name, prefix)
        elif len(args) >= 2:
            if len(args) > 2:
                ticket_id = args[2]
            else:
                ticket_id = None

            if require_ticket_id == "true":
                if len(args) < 3 and not _name_has_embedded_ticket(args[1], prefix):
                    sys.exit("Usage: git %s new <%s_name> <ticket_id>" % (prefix, prefix))

            new_feature(args[1], prefix, ticket_id)
        else:
            sys.exit("Usage: git %s new <%s_name>" % (prefix, prefix))
    elif len(args) and args[0].lower() == "finish":
        if len(args) == 1:
            finish_feature(None, prefix)
        elif len(args) == 2:
            finish_feature(args[1], prefix)
        else:
            sys.exit("Usage: git %s finish [%s_name]" % (prefix, prefix))
    else:
        sys.exit("Usage: git %s <new/finish> <%s_name>" % (prefix, prefix))


# Console script entry points for packaging
def cli_feature():
    return run("feature", sys.argv[1:])


def cli_hotfix():
    return hotfix(sys.argv[1:])


def cli_release():
    return release(sys.argv[1:])


def cli_stable():
    return stable(sys.argv[1:])


def cli_pullrequest():
    return pullrequest(sys.argv[1:])


def cli_releasecandidate():
    return run("releasecandidate", sys.argv[1:])
