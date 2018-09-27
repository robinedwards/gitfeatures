from subprocess import check_output, CalledProcessError
import datetime
import re
import webbrowser
import os
import sys
import six
from six.moves import input

master_branch = os.environ.get('GITFEATURES_MASTER_BRANCH', 'master')
repo = os.environ.get('GITFEATURES_REPO', 'github')

master_branch = os.environ.get('GITFEATURES_MASTER_BRANCH', 'master')
repo = os.environ.get('GITFEATURES_REPO', 'github')


def _call(args):
    try:
        return check_output(args).decode('utf-8')
    except CalledProcessError:
        sys.exit(__name__ + ": none zero exit status executing: " + " ".join(args))  # noqa


def new_feature(name, prefix):
    name = re.sub('\W', '_', name)
    if _current_branch() != master_branch:
        print(_current_branch(), master_branch)
        sys.exit(__name__ + ": you may only start {} from {} branch".format(prefix, master_branch))  # noqa

    _call(["git", "remote", "update", "origin"])
    new_branch = "%s_%s" % (prefix, name)

    if _branch_exists(new_branch):
        sys.exit(__name__ + ": local or remote branch already exists: " + new_branch)  # noqa

    _call(["git", "checkout", "-b", new_branch])
    _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])


def finish_feature(name, prefix):
    cur_branch = _current_branch()

    if name:
        branch = prefix + '_' + name
        if branch == cur_branch:
            _call(["git", "checkout", master_branch])
    elif cur_branch != master_branch:
        branch = cur_branch
        _call(["git", "checkout", master_branch])
    else:
        sys.exit(__name__ + ": please provide a branch name if on {}".format(master_branch))

    _call(["git", "remote", "update", "origin"])

    commits = _call(["git", "log", '--oneline', branch, '^origin/{}'.format(master_branch)])
    if commits:
        sys.exit(
            __name__ + ": " + branch
            + " contains commits that are not in {}:\n".format(master_branch) + commits
            + "\nraise a pull request and get them merged in.")
    else:
        _call(["git", "push", "origin", ":" + branch])
        _call(["git", "branch", "-D", branch])


def stable(args):
    if (len(args) > 0 and args[0] == 'new'):
        date = datetime.datetime.now()
        new_branch = 'stable_{}'.format(date.strftime('%Y%m%d'))

        _call(["git", "checkout", "-b", new_branch])
        _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])

        stable_branches = _get_stable_branches()
        if len(stable_branches) > 3:
            print("you have more than 3 stable branches, shall I delete the eldest one? [y/n]")  # noqa
            if input().lower() == 'y':
                branch = stable_branches[0]
                _call(["git", "push", "origin", "--delete", branch])
                _call(["git", "branch", "-D", branch])
    else:
        # checkout the latest stable branch
        stable_branches = _get_stable_branches()
        if stable_branches:
            branch = stable_branches[-1]
            _call(["git", "checkout", branch])
        else:
            print("No stable branches")


def pullrequest(args):
    branch = _current_branch()
    if branch == master_branch:
        sys.exit(__name__ + ": can't issue pull requests on {}".format(master_branch))

    # check its up to date with remote master if not pull
    _call(['git', 'remote', 'update', 'origin'])
    commits = _call(['git', 'log', '--oneline', '^' + branch, 'origin/{}'.format(master_branch)])
    if commits:
        print("Your branch is behind origin/{} so cannot be automatically merged.".format(master_branch))  # noqa
        print(commits)
        print("Do you wish to update and merge {} (If conflicts occur, you will be able to fix them)? [y/n]".format(master_branch))  # noqa
        if input().lower() == 'y':
            _call(['git', 'checkout', master_branch])
            _call(['git', 'pull'])
            _call(['git', 'checkout', branch])
            try:
                print("git merge {}".format(master_branch))
                output = check_output(['git', 'merge', master_branch])
                print(output)
                print("Congratulations, successfully merged {}".format(master_branch))
            except CalledProcessError as e:
                if 'CONFLICT' in e.output:
                    err =  e.output + "\n\nUnlucky! You have work to do. Fix the above conflicts and run git pullrequest again"  # noqa
                    sys.exit(err)
                else:
                    raise()

    # check if there are any unpushed commits
    commits = _call(['git', 'log', '--oneline', branch, '^origin/' + branch])
    if commits:
        print("You have unpushed commits:")
        print(commits)
        print("Push commits to origin [y/n]")
        if input().lower() == 'y':
            _call(['git', 'push', 'origin', branch + ':' + branch])

    origin = _call(["git", "config", "--get", "remote.origin.url"])
    name = origin.split(':')[1].replace(".git\n", '')
    url = _get_pullrequest_url(name, branch)
    if (len(args) > 0 and args[0] == '--dry-run') or os.environ.get('CONSOLEONLY', False):  # noqa
        print(url)
    else:
        webbrowser.open_new_tab(url)

def _get_pullrequest_url(name, branch):

    if repo == 'github':
        url = "https://github.com/" + name + "/pull/new/" + branch
    elif repo == 'bitbucket':
        url = "https://bitbucket.org/" + name + "/pull-requests/new?t=1&source=" + branch
    return url

def _current_branch():
    output = _call(["git", "branch"])
    branch = re.search('^\* (.+)$', output, flags=re.M).group(1)
    if not branch:
        sys.exit(__name__ + ": unable to detect current branch")
    else:
        return branch


def _branch_exists(name):
    branch_list = _call(["git", "branch", "-a"])
    return 1 if re.search('' + name + '$', branch_list, flags=re.M) else 0


def _get_stable_branches():
    _call(["git", "remote", "update", "origin"])
    try:
        branch_list = check_output("git branch -r | grep -e '\/stable_\d\d\d\d\d\d\d\d'", shell=True).strip()  # noqa
        branch_list = branch_list.split('\n')
        branch_list = map(lambda it: it.split('/')[1].strip(), branch_list)

        return branch_list
    except CalledProcessError:
        return []


def run(prefix, args):
    if len(args) and args[0].lower() == 'new':
        if prefix == 'releasecandidate':
            if len(args) == 2:
                new_feature(args[1], prefix)
            else:
                name = str(datetime.date.today())
                new_feature(name, prefix)
        elif len(args) == 2:
            new_feature(args[1], prefix)
        else:
            sys.exit("Usage: git %s new <%s_name>" % (prefix, prefix))
    elif len(args) and args[0].lower() == 'finish':
        if len(args) == 1:
            finish_feature(None, prefix)
        elif len(args) == 2:
            finish_feature(args[1], prefix)
        else:
            sys.exit("Usage: git %s finish [%s_name]" % (prefix, prefix))
    else:
        sys.exit("Usage: git %s <new/finish> <%s_name>" % (prefix, prefix))
