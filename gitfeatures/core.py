import os
import re
import sys
import datetime
import webbrowser
from subprocess import CalledProcessError, check_output

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
        new_branch = parsed_branch if parsed_branch else name
    else:
        new_branch = _get_branch_name(prefix, name, ticket_id)
    _debug(f"Creating new branch: {new_branch}")

    if _branch_exists(new_branch):
        sys.exit(__name__ + ": local or remote branch already exists: " + new_branch)  # noqa

    _call(["git", "checkout", "-b", new_branch])
    _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])


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
    name = origin.split(":")[1].replace(".git\n", "")
    print("name", name)
    print("branch", branch)
    url = _get_pullrequest_url(name, branch)
    if (len(args) > 0 and args[0] == "--dry-run") or os.environ.get("CONSOLEONLY", False):  # noqa
        print(url)
    else:
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
        branch_list = (
            check_output(
                f"git branch -r | grep -e '\/{branch_type}{branch_seperator}\d\d\d\d\d\d\d\d'",  # noqa
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
