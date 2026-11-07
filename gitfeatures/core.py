import os
import re
import sys
import json
import datetime
import webbrowser
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Tuple, Optional
from subprocess import STDOUT, DEVNULL, CalledProcessError, check_output

import jinja2  # Airflow uses Jinja2 for templating

CONFIG_FILENAME = ".gitfeatures"

# Each setting is resolved from, in order: its environment variable, its key in the repo's
# .gitfeatures file (git-config format, read with `git config --file`), then its default.
# (module attribute, environment variable, .gitfeatures key, default)
SETTINGS = (
    ("repo", "GITFEATURES_REPO", "gitfeatures.repo", "github"),
    ("master_branch", "GITFEATURES_MASTER_BRANCH", "gitfeatures.masterBranch", "main"),
    ("merge_strategy", "GITFEATURES_STRATEGY", "gitfeatures.strategy", "merge"),
    ("fork_pr_strategy", "GITFEATURES_FORK_PR_STRATEGY", "gitfeatures.forkPrStrategy", ""),
    ("branch_seperator", "GITFEATURES_BRANCH_SEPERATOR", "gitfeatures.branchSeparator", "_"),
    # None means "same as the branch separator"
    ("ticket_seperator", "GITFEATURES_TICKET_SEPERATOR", "gitfeatures.ticketSeparator", None),
    ("ticket_prefix", "GITFEATURES_TICKET_PREFIX", "gitfeatures.ticketPrefix", ""),
    ("require_ticket_id", "GITFEATURES_REQUIRE_TICKETID", "gitfeatures.requireTicketId", "false"),
    ("debug_enabled", "GITFEATURES_DEBUG", "gitfeatures.debug", "false"),
    ("changelog_enabled", "GITFEATURES_CHANGELOG_ENABLED", "changelog.enabled", "false"),
    # Path of the changelog template, absolute or relative to the repo root. Empty means "not configured".
    ("changelog_template_path", "GITFEATURES_CHANGELOG_TEMPLATE", "changelog.template", ""),
)
BOOLEAN_SETTINGS = ("require_ticket_id", "debug_enabled", "changelog_enabled")
_TRUTHY = ("1", "true", "yes", "on")

# Set by load_settings(); module-level so the rest of this module can read them as globals.
repo = master_branch = merge_strategy = fork_pr_strategy = ""
branch_seperator = ticket_seperator = ticket_prefix = ""
require_ticket_id = debug_enabled = changelog_enabled = False
changelog_template_path = ""
config_path_loaded: Optional[str] = None
# For each setting, where its value came from: the environment variable, the .gitfeatures key, or "default".
setting_sources: Dict[str, str] = {}


def _is_truthy(value) -> bool:
    return str(value).strip().lower() in _TRUTHY


def _repo_config_path() -> Optional[str]:
    """
    Return the path of the .gitfeatures file at the root of the current repo, or None outside a repo.
    The file does not have to exist.
    """
    try:
        root = check_output(["git", "rev-parse", "--show-toplevel"], stderr=DEVNULL).decode("utf-8").strip()
    except (CalledProcessError, OSError):
        return None
    return os.path.join(root, CONFIG_FILENAME) if root else None


def _read_config_file(path: Optional[str]) -> Dict[str, str]:
    """
    Read a git-config formatted file into a dict keyed by lower-cased "section.name".
    A key with no value (a bare boolean such as "enabled") reads as "true".
    """
    if not path or not os.path.isfile(path):
        return {}
    try:
        output = check_output(["git", "config", "--file", path, "--list", "-z"], stderr=STDOUT)
    except CalledProcessError as e:
        sys.exit(f"{__name__}: unable to read {path}: {e.output.decode('utf-8').strip()}")
    values = {}
    for entry in output.decode("utf-8").split("\0"):
        if not entry:
            continue
        key, sep, value = entry.partition("\n")
        values[key.lower()] = value if sep else "true"
    return values


def load_settings(config_path: Optional[str] = None, environ=None) -> Dict[str, Any]:
    """
    Resolve every setting in SETTINGS and store it on this module.
    Environment variables win over the .gitfeatures file at config_path, which wins over the defaults.
    When an environment variable overrides a different value from the file, a notice goes to stderr.
    Returns the resolved settings.
    """
    environ = os.environ if environ is None else environ
    config = _read_config_file(config_path)
    resolved: Dict[str, Any] = {}
    sources: Dict[str, str] = {}
    for attr, env_var, key, default in SETTINGS:
        file_value = config.get(key.lower())
        if env_var in environ:
            value = environ[env_var]
            sources[attr] = env_var
            if file_value is not None and not _same_setting_value(attr, value, file_value):
                print(
                    f"gitfeatures: {env_var}={value!r} overrides {key} = {file_value!r} from {config_path}",
                    file=sys.stderr,
                )
        elif file_value is not None:
            value = file_value
            sources[attr] = f"{key} in {config_path}"
        else:
            value = default
            sources[attr] = "default"
        resolved[attr] = value
    if resolved["ticket_seperator"] is None:
        resolved["ticket_seperator"] = resolved["branch_seperator"]
    for attr in BOOLEAN_SETTINGS:
        resolved[attr] = _is_truthy(resolved[attr])
    globals().update(resolved)
    globals()["setting_sources"] = sources
    globals()["config_path_loaded"] = config_path
    return resolved


def _same_setting_value(attr, a, b) -> bool:
    if attr in BOOLEAN_SETTINGS:
        return _is_truthy(a) == _is_truthy(b)
    return a == b


def load_repo_settings() -> Dict[str, Any]:
    """
    Resolve settings for the repo in the current directory, including its .gitfeatures file.
    Every command calls this before doing anything else.
    """
    return load_settings(_repo_config_path())


# Environment variables and defaults only, until a command loads the repo's .gitfeatures file.
load_settings()


def _debug(message):
    if debug_enabled:
        print(f"[gitfeatures] {message}")


def _call(args):
    try:
        return check_output(args).decode("utf-8")
    except CalledProcessError:
        sys.exit(__name__ + ": none zero exit status executing: " + " ".join(args))  # noqa


def _confirm() -> bool:
    """Read a y/n answer from stdin. Running out of input (e.g. too few answers piped in) counts as no."""
    try:
        return input().strip().lower() == "y"
    except EOFError:
        print("(no answer on stdin, taking that as no)")
        return False


def _github_token() -> Optional[str]:
    """GITHUB_TOKEN or GH_TOKEN, else the token the GitHub CLI is logged in with, if it is installed."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        return check_output(["gh", "auth", "token"], stderr=DEVNULL).decode("utf-8").strip() or None
    except (CalledProcessError, OSError):
        return None


def _git_output(args) -> Optional[str]:
    """Run git quietly and return its stripped output, or None if it fails."""
    try:
        return check_output(["git", *args], stderr=DEVNULL).decode("utf-8").strip()
    except (CalledProcessError, OSError):
        return None


def _ref_exists(ref) -> bool:
    return _git_output(["rev-parse", "--verify", "--quiet", ref]) is not None


# Each branch's base (the branch it was created from, and the one its pull request goes into) is kept in
# the repo's git config as branch.<name>.gitfeaturesBase. Git renames and deletes it with the branch.
BASE_CONFIG_KEY = "gitfeaturesBase"
_CREATED_FROM = re.compile(r"^branch: Created from (.+)$")


def _record_base_branch(branch, base):
    _call(["git", "config", f"branch.{branch}.{BASE_CONFIG_KEY}", base])


def _detached_at_master_tip() -> bool:
    """True when HEAD is detached at the commit origin/<master branch> (or the local master branch) points to."""
    if _git_output(["symbolic-ref", "-q", "HEAD"]) is not None:
        return False
    head = _git_output(["rev-parse", "HEAD"])
    tips = (
        _git_output(["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
        for ref in (f"refs/remotes/origin/{master_branch}", f"refs/heads/{master_branch}")
    )
    return head is not None and head in tips


def _base_for_new_branch(new_branch, start, requested=None, at_master_tip=False) -> str:
    """
    The base to record for new_branch, created from start (the current branch, or a detached HEAD):
    1. requested (--base <branch>);
    2. start, when it is a local branch;
    3. the master branch, when HEAD is detached at its tip (at_master_tip);
    4. otherwise ask, defaulting to the master branch. With no answer on stdin, exit and ask for --base.
    Anything but a local start branch has to exist on origin. Called before the branch is created, so a
    bad answer leaves nothing behind.
    """
    if not requested and _ref_exists(f"refs/heads/{start}"):
        return start
    if requested:
        base, source = requested, "from --base"
    elif at_master_tip:
        base, source = master_branch, f"HEAD is detached at the tip of {master_branch}"
    else:
        print(f"HEAD is detached. Which branch is {new_branch} based on? [{master_branch}]")
        try:
            answer = input().strip()
        except EOFError:
            sys.exit(f"{__name__}: no answer on stdin. Rerun with --base <branch>, naming {new_branch}'s base branch.")
        base, source = answer or master_branch, "answered"
    if not _ref_exists(f"refs/remotes/origin/{base}"):
        sys.exit(f"{__name__}: the base branch {base} ({source}) is not on origin. Push it, or pass --base <branch>.")
    print(f"Base branch: {base} ({source})")
    return base


def _base_branch_from_reflog(branch) -> Optional[str]:
    """
    The branch git's reflog says branch was created from, such as release_x for "Created from origin/release_x".
    None when git recorded only HEAD or a commit, the reflog has expired, or that branch is not on origin.
    """
    entries = _git_output(["reflog", "show", "--format=%gs", f"refs/heads/{branch}", "--"])
    match = _CREATED_FROM.match(entries.splitlines()[-1]) if entries else None
    if not match:
        return None
    start = re.sub(r"^(refs/heads/|refs/remotes/origin/|remotes/origin/|origin/)", "", match.group(1).strip())
    if start in ("HEAD", branch) or not _ref_exists(f"refs/remotes/origin/{start}"):
        return None
    return start


def _resolve_base_branch(branch, requested=None) -> str:
    """
    Return the branch that branch is brought up to date with and has its pull request opened against:
    1. requested (git pullrequest --base <branch>);
    2. branch.<branch>.gitfeaturesBase, recorded when gitfeatures created the branch or by an earlier run;
    3. the branch git's reflog says it was created from;
    4. the configured base branch, only once you confirm it.
    The answer is recorded in branch.<branch>.gitfeaturesBase so later runs use it.
    """
    recorded = _git_output(["config", "--get", f"branch.{branch}.{BASE_CONFIG_KEY}"])
    if requested:
        base, source = requested, "from --base"
    elif recorded:
        base, source = recorded, f"recorded in branch.{branch}.{BASE_CONFIG_KEY}"
    else:
        base, source = _base_branch_from_reflog(branch), "the branch it was created from"
        if not base:
            print(f"gitfeatures doesn't know which branch {branch} was created from. Was it {master_branch}? [y/n]")
            if not _confirm():
                sys.exit(f"Run git pullrequest --base <branch>, naming the branch {branch} was created from.")
            base, source = master_branch, "confirmed"
    if base == branch:
        sys.exit(f"{__name__}: {branch} can't be its own base branch. Pass --base <branch>.")
    if not _ref_exists(f"refs/remotes/origin/{base}"):
        sys.exit(f"{__name__}: the base branch {base} ({source}) is not on origin. Push it, or pass --base <branch>.")
    if base != recorded:
        _record_base_branch(branch, base)
    print(f"Base branch: {base} ({source})")
    return base


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
    Drops leading branch-type prefix like 'feature/' to avoid nested directories.
    """
    filename_branch = branch.split("/", 1)[1] if "/" in branch else branch
    return os.path.join("changelog", f"{filename_branch}.md")


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


""  # Story template removed; only changelog template is supported


DEFAULT_CHANGELOG_TEMPLATE = os.path.join(os.path.dirname(__file__), "templates", "changelog-template.md")
# Picked up from the repo root when changelog.template is not set, for repos that relied on it before
# the setting existed.
LEGACY_CHANGELOG_TEMPLATE = "changelog-template.md"


def _resolve_repo_path(path: str) -> str:
    return path if os.path.isabs(path) else os.path.join(_get_repo_root(), path)


def _changelog_template_file() -> str:
    """
    Return the changelog template to use, in order:
    1. changelog.template (or GITFEATURES_CHANGELOG_TEMPLATE), absolute or relative to the repo root;
    2. changelog-template.md in the repo root;
    3. the default template bundled with gitfeatures.
    A configured template that does not exist is reported on stderr and the bundled default is used.
    """
    if changelog_template_path:
        path = _resolve_repo_path(changelog_template_path)
        if os.path.isfile(path):
            return path
        source = setting_sources.get("changelog_template_path", "configuration")
        print(
            f"gitfeatures: changelog template {path} (set by {source}) does not exist, so the bundled default is used",
            file=sys.stderr,
        )
        return DEFAULT_CHANGELOG_TEMPLATE
    legacy = _resolve_repo_path(LEGACY_CHANGELOG_TEMPLATE)
    if os.path.isfile(legacy):
        return legacy
    return DEFAULT_CHANGELOG_TEMPLATE


def _read_changelog_template() -> Optional[str]:
    path = _changelog_template_file()
    _debug(f"Using changelog template {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception as e:
        _debug(f"Failed to read changelog template {path}: {e}")
        return None


def init_changelog_template(out: Optional[str] = None, force: bool = False) -> str:
    """
    Copy the bundled default changelog template into the repo so it can be edited, and record it as
    changelog.template in the repo's .gitfeatures file. Returns the path written.
    """
    repo_root = _get_repo_root()
    target_setting = out or changelog_template_path or LEGACY_CHANGELOG_TEMPLATE
    target = _resolve_repo_path(target_setting)
    if os.path.exists(target) and not force:
        sys.exit(f"{target} already exists. Use --force to overwrite it with the default template.")
    parent = os.path.dirname(target)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(DEFAULT_CHANGELOG_TEMPLATE, "r", encoding="utf-8") as src, open(target, "w", encoding="utf-8") as dst:
        dst.write(src.read())

    config_file = os.path.join(repo_root, CONFIG_FILENAME)
    relative = os.path.relpath(target, repo_root)
    stored = target if relative.startswith(os.pardir) else relative
    _call(["git", "config", "--file", config_file, "changelog.template", stored])
    print(f"Wrote {target}")
    print(f"Set changelog.template = {stored} in {config_file}")
    if "changelog.enabled" not in _read_config_file(config_file):
        _call(["git", "config", "--file", config_file, "changelog.enabled", "true"])
        print(f"Set changelog.enabled = true in {config_file}")
    print(f"Edit the template, then commit it and {CONFIG_FILENAME}.")
    return target


def _build_changelog_context(
    branch: str, ticket_identifier: Optional[str], linear_issue: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Build the Jinja2 context for rendering the changelog template.
    """
    # Suggested fields
    title = (linear_issue.get("title") if linear_issue else "") or branch
    background = (linear_issue.get("description") if linear_issue else "") or ""
    repo_origin = ""
    repo_full_name = ""
    try:
        # Not _call(): it exits when the repo has no origin remote, and the changelog does not need one.
        repo_origin = check_output(["git", "config", "--get", "remote.origin.url"], stderr=DEVNULL).decode("utf-8")
        repo_full_name = _get_repo_full_name_from_origin_url(repo_origin)
    except (CalledProcessError, OSError):
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
            "number": linear_issue.get("number"),
            "createdAt": linear_issue.get("createdAt"),
            "updatedAt": linear_issue.get("updatedAt"),
            "priority": linear_issue.get("priority"),
            "estimate": linear_issue.get("estimate"),
            "team": linear_issue.get("team"),
            "state": linear_issue.get("state"),
            "assignee": linear_issue.get("assignee"),
            "labels": linear_issue.get("labels") or [],
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
        "now": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
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
    query Issues($teamKey: String!, $number: Float!) {
      issues(filter: { number: { eq: $number }, team: { key: { eq: $teamKey } } }, first: 1) {
        nodes {
          id
          identifier
          number
          title
          description
          url
          createdAt
          updatedAt
          priority
          estimate
          team { id key name }
          state { id name type color }
          assignee { id name displayName email }
          labels(first: 50) { nodes { id name color } }
        }
      }
    }
    """
    # Linear's schema expects number as a Float
    payload = {"query": query, "variables": {"teamKey": team_key, "number": float(number)}}
    data = json.dumps(payload).encode("utf-8")
    # Linear expects the API key directly in the Authorization header (no 'Bearer ' prefix)
    auth_value = (token or "").strip()
    if auth_value.lower().startswith("bearer "):
        auth_value = auth_value[7:].strip()
    headers = {
        "Authorization": auth_value,
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
                labels_nodes = (((node or {}).get("labels") or {}).get("nodes")) or []
                labels = [
                    {"id": it.get("id"), "name": it.get("name"), "color": it.get("color")} for it in labels_nodes
                ]
                state = node.get("state") or {}
                team = node.get("team") or {}
                assignee = node.get("assignee") or {}
                return {
                    "identifier": node.get("identifier"),
                    "number": node.get("number"),
                    "title": node.get("title"),
                    "description": node.get("description") or "",
                    "url": node.get("url"),
                    "createdAt": node.get("createdAt"),
                    "updatedAt": node.get("updatedAt"),
                    "priority": node.get("priority"),
                    "estimate": node.get("estimate"),
                    "team": {"key": team.get("key"), "name": team.get("name"), "id": team.get("id")},
                    "state": {
                        "name": state.get("name"),
                        "type": state.get("type"),
                        "color": state.get("color"),
                        "id": state.get("id"),
                    },
                    "assignee": {
                        "id": assignee.get("id"),
                        "name": assignee.get("name"),
                        "displayName": assignee.get("displayName"),
                        "email": assignee.get("email"),
                    },
                    "labels": labels,
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
    payload = {"title": title, "head": head_branch, "base": base_branch, "draft": True}
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


def new_feature(name, prefix, ticket_id=None, requested_base=None):
    # Allow alnum, underscore, hyphen, and slash in branch inputs
    name = re.sub(r"[^\w\-/]", "_", name)
    original_branch = _current_branch()
    at_master_tip = _detached_at_master_tip()
    if original_branch != master_branch and not at_master_tip and not requested_base:
        print(_current_branch(), master_branch)
        print(
            "You aren't on your main {} branch. Are you sure you wish to create a branch from {}? [y/n]".format(
                master_branch, original_branch
            )
        )  # noqa
        if not _confirm():
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
                    f"Detected ticket in input. normalized_ticket={normalized_ticket}, "
                    f"slug={slug}, branch={parsed_branch}"
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

    base = _base_for_new_branch(new_branch, original_branch, requested_base, at_master_tip)
    _call(["git", "checkout", "-b", new_branch])
    _record_base_branch(new_branch, base)
    _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])
    # Create changelog file for this branch if feature is enabled and file not present
    if changelog_enabled:
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


def _worktree_with_branch(branch) -> Optional[str]:
    """The path of the worktree that has branch checked out, or None."""
    path = None
    for line in (_git_output(["worktree", "list", "--porcelain"]) or "").splitlines():
        if line.startswith("worktree "):
            path = line.removeprefix("worktree ")
        elif line == f"branch refs/heads/{branch}":
            return path
    return None


def _leave_current_branch(base_branch):
    """
    Move off the current branch so it can be deleted: onto the base branch when no worktree has it checked
    out, otherwise onto a detached HEAD at origin/<base>, so another worktree's checkout is never needed.
    """
    if _ref_exists(f"refs/heads/{base_branch}") and not _worktree_with_branch(base_branch):
        _call(["git", "checkout", base_branch])
    else:
        _call(["git", "checkout", "--detach", f"origin/{base_branch}"])
        print(f"{base_branch} is checked out in another worktree, so HEAD is now detached at origin/{base_branch}.")


def finish_feature(name, prefix, requested_base=None):
    cur_branch = _current_branch()

    if name:
        branch = _get_branch_name(prefix, name)
    elif cur_branch != master_branch:
        branch = cur_branch
    else:
        sys.exit(__name__ + ": please provide a branch name if on {}".format(master_branch))
    if branch != cur_branch:
        other_worktree = _worktree_with_branch(branch)
        if other_worktree:
            sys.exit(f"{__name__}: {branch} is checked out in {other_worktree}. Run this there instead.")

    _call(["git", "remote", "update", "origin"])
    base_branch = _resolve_base_branch(branch, requested_base)

    commits = _call(["git", "log", "--oneline", branch, "^origin/{}".format(base_branch)])
    if commits:
        sys.exit(
            __name__
            + ": "
            + branch
            + " contains commits that are not in {}:\n".format(base_branch)
            + commits
            + "\nraise a pull request and get them merged in."
        )
    if branch == cur_branch:
        _leave_current_branch(base_branch)
    if _git_output(["ls-remote", "--exit-code", "--heads", "origin", f"refs/heads/{branch}"]) is not None:
        _call(["git", "push", "origin", ":" + branch])
    else:
        # Already deleted on origin, e.g. by GitHub after the merge. Drop the stale origin/<branch> too.
        print(f"{branch} has already been deleted on origin.")
        if _ref_exists(f"refs/remotes/origin/{branch}"):
            _call(["git", "branch", "--delete", "--remotes", f"origin/{branch}"])
    _call(["git", "branch", "-D", branch])


CLEANUP_USAGE = "Usage: git cleanup [--dry-run] [--yes]"


def _is_ancestor(commit, of) -> bool:
    return _git_output(["merge-base", "--is-ancestor", commit, of]) is not None


def _cleanup_reason(branch, upstream_track) -> Optional[str]:
    """
    Why branch can be deleted locally: merged into origin/<its base branch> or origin/<masterBranch>, or
    its upstream branch has been deleted on origin (as GitHub does after a squash merge). None to keep it.
    """
    recorded = _git_output(["config", "--get", f"branch.{branch}.{BASE_CONFIG_KEY}"])
    for base in dict.fromkeys(filter(None, (recorded, _base_branch_from_reflog(branch), master_branch))):
        if not _ref_exists(f"refs/remotes/origin/{base}"):
            continue
        if _is_ancestor(f"refs/heads/{branch}", f"refs/remotes/origin/{base}"):
            return f"merged into origin/{base}"
    if upstream_track == "[gone]":
        return "deleted on origin"
    return None


def cleanup(args):
    """
    Delete local branches that are merged into their base branch on origin, or whose upstream branch has
    been deleted on origin. Branches checked out in any worktree, and masterBranch, are kept. Only local
    branches are deleted; nothing is pushed.
    """
    load_repo_settings()
    unknown = [arg for arg in args if arg not in ("--dry-run", "--yes", "-y")]
    if unknown:
        sys.exit(CLEANUP_USAGE)
    dry_run = "--dry-run" in args
    assume_yes = "--yes" in args or "-y" in args

    _call(["git", "fetch", "--prune", "--quiet", "origin"])
    refs = _call(["git", "for-each-ref", "--format=%(refname)%09%(upstream:track)%09%(worktreepath)", "refs/heads"])
    candidates = []
    for line in refs.splitlines():
        ref, upstream_track, worktree = line.split("\t")
        branch = ref.removeprefix("refs/heads/")
        if worktree or branch == master_branch:
            continue
        reason = _cleanup_reason(branch, upstream_track)
        if reason:
            candidates.append((branch, reason))

    if not candidates:
        print("Nothing to clean up.")
        return
    width = max(len(branch) for branch, _ in candidates)
    for branch, reason in candidates:
        print(f"  {branch:<{width}}  {reason}")
    if dry_run:
        return
    if not assume_yes:
        print(f"Delete these {len(candidates)} local branches? [y/n]")
        if not _confirm():
            sys.exit("Ok, Exiting")
    for branch, _ in candidates:
        _call(["git", "branch", "-D", branch])
        print(f"Deleted {branch}")


def _branch_func(branch_type, args):
    load_repo_settings()
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

        base = _base_for_new_branch(new_branch, _current_branch(), at_master_tip=_detached_at_master_tip())
        _call(["git", "checkout", "-b", new_branch])
        _record_base_branch(new_branch, base)
        _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])

        branches = _get_branches(branch_type)
        if len(branches) > 3:
            branch = branches[0]
            print(
                f"you have more than 3 {branch_type} branches, shall I delete the eldest one ({branch})? [y/n]"
            )  # noqa
            if _confirm():
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


PULLREQUEST_USAGE = "Usage: git pullrequest [--base <branch>] [--dry-run]"


def _pop_base_option(args, usage):
    """Split `--base <branch>` out of args, returning (branch or None, the other args)."""
    if "--base" not in args:
        return None, list(args)
    index = args.index("--base")
    if index + 1 >= len(args) or args[index + 1].startswith("-"):
        sys.exit(usage)
    return args[index + 1], [arg for i, arg in enumerate(args) if i not in (index, index + 1)]


def pullrequest(args):
    load_repo_settings()
    requested_base, args = _pop_base_option(args, PULLREQUEST_USAGE)
    dry_run = "--dry-run" in args

    branch = _current_branch()
    if branch == master_branch:
        sys.exit(__name__ + ": can't issue pull requests on {}".format(master_branch))

    _call(["git", "remote", "update", "origin"])
    base_branch = _resolve_base_branch(branch, requested_base)

    # check it is up to date with the base branch on origin, and offer to update it if not
    base = f"origin/{base_branch}"
    commits = _call(["git", "log", "--oneline", "^" + branch, base])
    if commits:
        print(f"Your branch is behind {base} so cannot be automatically {merge_strategy}d.")
        print(commits)
        print(
            f"Do you wish to fetch {base} and {merge_strategy} {branch} with it "
            "(If conflicts occur, you will be able to fix them)? [y/n]"
        )
        if _confirm():
            _call(["git", "fetch", "origin", base_branch])
            _update_branch_from(base)

    # check if there are any unpushed commits
    commits = _call(["git", "log", "--oneline", branch, "^origin/" + branch])
    if commits:
        print("You have unpushed commits:")
        print(commits)
        print("Push commits to origin [y/n]")
        if _confirm():
            _call(["git", "push", "origin", branch + ":" + branch])

    origin = _call(["git", "config", "--get", "remote.origin.url"])
    print("origin", origin)
    name = _get_repo_full_name_from_origin_url(origin)
    print("name", name)
    print("branch", branch)
    url = _get_pullrequest_url(name, branch, base_branch)
    if dry_run or os.environ.get("CONSOLEONLY", False):
        print(url)
    else:
        # If a GitHub token is available, attempt to create the PR via API
        token = _github_token() if repo == "github" else None
        if repo == "github" and not token:
            print("No GITHUB_TOKEN, GH_TOKEN or `gh auth login`, so the pull request was not created.")
        if token:
            body = _read_changelog_body(branch) if changelog_enabled else None
            ok, resp = _create_github_pr_with_token(name, branch, base_branch, body, token)
            if ok:
                pr_url = resp.get("html_url") or url
                print(f"Created PR: {pr_url}")
                # Open the created PR directly unless console-only requested
                if not os.environ.get("CONSOLEONLY", False):
                    try:
                        webbrowser.open_new_tab(pr_url)
                    except Exception:
                        pass
                return
            else:
                print(f"Failed to create the pull request via the GitHub API: {resp}")
        print(f"Open it in your browser: {url}")
        webbrowser.open_new_tab(url)


def _update_branch_from(base):
    """
    Merge base (e.g. origin/main) into the current branch, or rebase the current branch onto it when the
    strategy is rebase. The base branch itself is never checked out, so this works in a git worktree while
    the base branch is checked out in another worktree.
    """
    command = ["git", merge_strategy, base]
    print(" ".join(command))
    try:
        output = check_output(command, stderr=STDOUT).decode("utf-8")
    except CalledProcessError as e:
        output = e.output.decode("utf-8")
        if "CONFLICT" in output:
            finish = "run `git rebase --continue`" if merge_strategy == "rebase" else "run `git commit`"
            sys.exit(
                f"{output}\n\nUnlucky! You have work to do. Fix the above conflicts, `git add` the fixed files, "
                f"{finish}, then run git pullrequest again."
            )
        sys.exit(f"{output}\n{__name__}: `{' '.join(command)}` failed, see git's message above.")
    print(output)
    print(f"Congratulations, successfully {merge_strategy}d {base}")


def _get_pullrequest_url(name, branch, base_branch):
    print("pullrequest", name, branch, base_branch, fork_pr_strategy)
    if repo == "github":
        if fork_pr_strategy == "private":
            url = f"https://github.com/{name}/compare/{base_branch}...{branch}"
        elif base_branch != master_branch:
            # pull/new/<branch> always targets the repository's default branch
            url = f"https://github.com/{name}/compare/{base_branch}...{branch}?expand=1"
        else:
            url = "https://github.com/" + name + "/pull/new/" + branch
    elif repo == "bitbucket":
        url = f"https://bitbucket.org/{name}/pull-requests/new?t=1&source={branch}&dest={base_branch}"
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
        # Sort branches by embedded date (YYYYMMDD) and optional suffix (e.g. HHMMSS)
        date_regex = re.compile(
            r"^"
            + re.escape(branch_type)
            + re.escape(branch_seperator)
            + r"(?P<date>\d{8})(?:"
            + re.escape(branch_seperator)
            + r"(?P<suffix>.+))?$"
        )

        def _sort_key(branch_name: str):
            m = date_regex.match(branch_name)
            if not m:
                return ("00000000", "")
            return (m.group("date") or "00000000", m.group("suffix") or "")

        branch_list.sort(key=_sort_key)
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
    load_repo_settings()
    if len(args) and args[0].lower() == "new":
        usage = "Usage: git %s new <%s_name> [--base <branch>]" % (prefix, prefix)
        requested_base, rest = _pop_base_option(args[1:], usage)
        args = [args[0], *rest]
        allowed_branch_types = ["releasecandidate", "stable", "release", "hotfix"]
        if prefix in allowed_branch_types:
            if len(args) == 2:
                new_feature(args[1], prefix, requested_base=requested_base)
            else:
                name = str(datetime.date.today())
                new_feature(name, prefix, requested_base=requested_base)
        elif len(args) >= 2:
            if len(args) > 2:
                ticket_id = args[2]
            else:
                ticket_id = None

            if require_ticket_id:
                if len(args) < 3 and not _name_has_embedded_ticket(args[1], prefix):
                    sys.exit("Usage: git %s new <%s_name> <ticket_id>" % (prefix, prefix))

            new_feature(args[1], prefix, ticket_id, requested_base)
        else:
            sys.exit("Usage: git %s new <%s_name> [--base <branch>]" % (prefix, prefix))
    elif len(args) and args[0].lower() == "finish":
        usage = "Usage: git %s finish [%s_name] [--base <branch>]" % (prefix, prefix)
        requested_base, rest = _pop_base_option(args[1:], usage)
        if len(rest) > 1:
            sys.exit(usage)
        finish_feature(rest[0] if rest else None, prefix, requested_base)
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


def cli_cleanup():
    return cleanup(sys.argv[1:])


CHANGELOG_USAGE = (
    "Usage: git-changelog [--branch <name>] [--ticket <id>] [--write] [--out <path>]\n"
    "       git-changelog --init-template [--out <path>] [--force]"
)


def _parse_args(args):
    """
    Minimal flag parser for preview commands.
    Supports:
      --branch <name>
      --ticket <identifier>
      --write
      --out <path>
      --init-template
      --force
    """
    opts = {"branch": None, "ticket": None, "write": False, "out": None, "init_template": False, "force": False}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--branch" and i + 1 < len(args):
            opts["branch"] = args[i + 1]
            i += 2
        elif a == "--ticket" and i + 1 < len(args):
            opts["ticket"] = args[i + 1]
            i += 2
        elif a == "--write":
            opts["write"] = True
            i += 1
        elif a == "--out" and i + 1 < len(args):
            opts["out"] = args[i + 1]
            i += 2
        elif a == "--init-template":
            opts["init_template"] = True
            i += 1
        elif a == "--force":
            opts["force"] = True
            i += 1
        else:
            print(f"Unrecognized or incomplete option: {a}")
            sys.exit(CHANGELOG_USAGE)
    return opts


def preview_changelog(args):
    """
    Render the changelog template using current context without creating a feature.
    """
    load_repo_settings()
    opts = _parse_args(args)
    if opts["init_template"]:
        if opts["branch"] or opts["ticket"] or opts["write"]:
            sys.exit(CHANGELOG_USAGE)
        init_changelog_template(opts["out"], opts["force"])
        return
    branch = opts["branch"] or _current_branch()
    ticket_identifier = opts["ticket"]

    # Try to detect ticket from branch if not provided, reusing branch parsing heuristics
    detected_ticket_identifier = None
    if ticket_identifier:
        detected_ticket_identifier = ticket_identifier
    else:
        if "/" in branch:
            rest = branch.split("/", 1)[1]
        else:
            rest = branch
        if ticket_seperator and ticket_prefix:
            pattern = re.compile(
                r"^(" + re.escape(ticket_prefix) + r")(\d+)" + re.escape(ticket_seperator) + r"(.*)$",
                re.IGNORECASE,
            )
            m = pattern.match(rest)
            if m:
                number = m.group(2)
                detected_ticket_identifier = f"{ticket_prefix}{number}"

    # Optional Linear fetch
    linear_issue = None
    linear_token = os.environ.get("LINEAR_API_KEY") or os.environ.get("LINEAR_TOKEN")
    if linear_token and detected_ticket_identifier:
        parsed = _extract_linear_team_and_number(detected_ticket_identifier)
        if parsed:
            team_key, number = parsed
            linear_issue = _fetch_linear_issue(team_key, number, linear_token)

    # Render from changelog template
    changelog_template = _read_changelog_template()
    if not changelog_template:
        sys.exit("Unable to read the changelog template. Run with GITFEATURES_DEBUG=1 for details.")
    context = _build_changelog_context(branch, detected_ticket_identifier, linear_issue)
    rendered = _render_changelog_template(changelog_template, context)
    if rendered is None:
        sys.exit("Failed to render changelog template.")

    if opts["write"]:
        target = opts["out"] or _get_changelog_path_for_branch(branch)
        parent = os.path.dirname(target)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(rendered)
        print(target)
    else:
        print(rendered)


def cli_changelog():
    return preview_changelog(sys.argv[1:])
