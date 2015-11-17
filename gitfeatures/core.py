from subprocess import check_output, CalledProcessError
import re
import webbrowser
import os
import sys


def _call(args):
    try:
        return check_output(args)
    except CalledProcessError:
        sys.exit(__name__ + ": none zero exit status executing: " + " ".join(args))


def new_feature(name, prefix):
    name = re.sub('\W', '_', name)
    if _current_branch() != 'master':
        sys.exit(__name__ + ": you may only start %ss from master branch" % prefix)

    _call(["git", "remote", "update", "origin"])
    new_branch = "%s_%s" % (prefix, name)

    if _branch_exists(new_branch):
        sys.exit(__name__ + ": local or remote branch already exists: " + new_branch)

    _call(["git", "checkout", "-b", new_branch])
    _call(["git", "push", "-u", "origin", new_branch + ":" + new_branch])


def finish_feature(name, prefix):
    cur_branch = _current_branch()

    if name:
        branch = prefix + '_' + name
        if branch == cur_branch:
            _call(["git", "checkout", "master"])
    elif cur_branch != 'master':
        branch = cur_branch
        _call(["git", "checkout", "master"])
    else:
        sys.exit(__name__ + ": please provide a branch name if on master")

    _call(["git", "remote", "update", "origin"])

    commits = _call(["git", "log", '--oneline', branch, '^origin/master'])
    if commits:
        sys.exit(__name__ + ": " + branch \
                + " contains commits that are not in master:\n" + commits \
                + "\nraise a pull request and get them merged in.")
    else:
        _call(["git", "push", "origin", ":" + branch])
        _call(["git", "branch", "-D", branch])


def pullrequest(args):
    branch = _current_branch()
    if branch == 'master':
        sys.exit(__name__ + ": can't issue pull requests on master")

    # check its up to date with remote master if not pull
    _call(['git', 'remote', 'update', 'origin'])
    commits = _call(['git', 'log', '--oneline', '^' + branch, 'origin/master'])
    if commits:
        print "Your branch is behind origin/master so cannot be automatically merged."
        print commits
        print "Do you wish to update and merge master (If conflicts occur, you will be able to fix them)? [y/n]"
        if raw_input().lower() == 'y':
            _call(['git', 'checkout', 'master'])
            _call(['git', 'pull'])
            _call(['git', 'checkout', branch])
            try:
                print "git merge master"
                output = check_output(['git', 'merge', 'master'])
                print output
                print "Congratulations, successfully merged master"
            except CalledProcessError as e:
                if 'CONFLICT' in e.output:
                    err =  e.output + "\n\nUnlucky! You have work to do. Fix the above conflicts and run git pullrequest again"
                    sys.exit(err)
                else:
                    raise()

    # check if there are any unpushed commits
    commits = _call(['git', 'log', '--oneline', branch, '^origin/' + branch])
    if commits:
        print "You have unpushed commits:"
        print commits
        print "Push commits to origin [y/n]"
        if raw_input().lower() == 'y':
            _call(['git', 'push', 'origin', branch + ':' + branch])

    origin = _call(["git", "config", "--get", "remote.origin.url"])
    name = origin.split(':')[1].replace(".git\n", '')
    url = "https://github.com/" + name + "/pull/new/" + branch
    if (len(args) > 0 and args[0] == '--dry-run') or os.environ.get('CONSOLEONLY', False):
        print url
    else:
        webbrowser.open_new_tab(url)


def _current_branch():
    output = _call(["git", "branch"])
    branch = re.search('^\* (.+)$', output, flags=re.M).group(1)
    if not branch:
        sys.exit(__name__ + ": unable to detect current branch")
    else:
        return branch


def _branch_exists(name):
    branch_list = _call(["git", "branch", "-a"])
    return 1 if re.search(name + '$', branch_list, flags=re.M) else 0


def run(prefix, args):
    if len(args) and args[0].lower() == 'new':
        if len(args) == 2:
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
