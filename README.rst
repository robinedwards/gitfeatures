============
git features
============

.. image:: https://github.com/robinedwards/gitfeatures/actions/workflows/tests.yml/badge.svg?branch=master
   :target: https://github.com/robinedwards/gitfeatures/actions/workflows/tests.yml
   :alt: tests

git helper scripts for managing feature branches and issuing pull requests. gitfeatures creates and
pushes consistently named branches, opens pull requests against the right base branch, cleans up
merged branches, and can write a changelog for each branch from a template you control.

.. contents::
   :local:
   :depth: 1

************
Requirements
************

- Python 3.10 or newer
- git, with a remote named ``origin``
- GitHub or Bitbucket for pull requests

************
Installation
************

::

    $ pip install git+https://github.com/robinedwards/gitfeatures.git

This installs the ``git feature``, ``git hotfix``, ``git release``, ``git stable``,
``git releasecandidate``, ``git pullrequest`` and ``git changelog`` commands.

To upgrade, run the same command with ``--upgrade``. See `Migrating from environment variables`_ if
you configured an earlier version with environment variables.

***********
Quick start
***********

gitfeatures works with no configuration for a GitHub repo whose base branch is ``main``:

::

    $ git feature new html_pruning      # creates and pushes feature_html_pruning
    $ git pullrequest                   # opens a pull request for the current branch
    $ git feature finish                # after the PR is merged: deletes the branch locally and on origin

To set a repo up for everyone who works on it, commit a ``.gitfeatures`` file:

::

    $ git config --file .gitfeatures gitfeatures.masterBranch develop
    $ git config --file .gitfeatures gitfeatures.ticketPrefix ENG-
    $ git changelog --init-template     # optional: per-branch changelogs from an editable template
    $ git add .gitfeatures changelog-template.md
    $ git commit -m "Configure gitfeatures"

*************
Configuration
*************

The .gitfeatures file
=====================

Settings for a repository live in a ``.gitfeatures`` file at the top of its working tree, committed
so everyone who works on the repo gets the same behaviour:

::

    [gitfeatures]
        repo = github
        masterBranch = develop
        strategy = rebase
        ticketPrefix = ENG-
        ticketSeparator = -
        requireTicketId = true

    [changelog]
        enabled = true
        template = .github/changelog-template.md

The file uses git's own config format (the same as ``.git/config``) and is read with
``git config --file .gitfeatures``, so you can edit it by hand or with git:

::

    $ git config --file .gitfeatures gitfeatures.masterBranch develop
    $ git config --file .gitfeatures --unset gitfeatures.masterBranch
    $ git config --file .gitfeatures --list

- Section and key names are case-insensitive.
- A key written without a value (``requireTicketId`` on its own line) means ``true``.
- Boolean settings are true for ``true``, ``1``, ``yes`` or ``on``. Any other value is false.
- Paths are absolute or relative to the top of the working tree.
- In a git worktree, the ``.gitfeatures`` of that worktree's checkout is used.
- A file git cannot parse stops every command with git's error message.

Never put tokens or other secrets in ``.gitfeatures``. It is meant to be committed, and gitfeatures only
reads secrets from the environment.

Environment variables
=====================

Every setting can also be set with an environment variable. The order of precedence is:

1. the environment variable;
2. the key in ``.gitfeatures``;
3. the default.

When an environment variable overrides a *different* value from ``.gitfeatures``, gitfeatures prints a
notice to stderr, for example:

::

    gitfeatures: GITFEATURES_MASTER_BRANCH='main' overrides gitfeatures.masterBranch = 'develop' from /path/to/repo/.gitfeatures

This makes a forgotten ``export`` in your shell profile visible. To override a setting for a single
command, set the variable for that command only:

::

    $ GITFEATURES_MASTER_BRANCH=release git pullrequest

Settings
========

Each setting as a ``.gitfeatures`` key and as an environment variable:

- ``gitfeatures.repo`` / ``GITFEATURES_REPO``: ``github`` (default) or ``bitbucket``.
- ``gitfeatures.masterBranch`` / ``GITFEATURES_MASTER_BRANCH``: Base branch that features are created
  from, compared against and merged into. Default: ``main``.
- ``gitfeatures.strategy`` / ``GITFEATURES_STRATEGY``: How ``git pullrequest`` brings a branch up to
  date with the base branch: ``merge`` (default) or ``rebase``.
- ``gitfeatures.forkPrStrategy`` / ``GITFEATURES_FORK_PR_STRATEGY``: If set to ``private`` on GitHub, uses
  the compare view instead of the new-PR shortcut.
- ``gitfeatures.branchSeparator`` / ``GITFEATURES_BRANCH_SEPERATOR``: Separator between the parts of a
  branch name. Default: ``_``.
- ``gitfeatures.ticketSeparator`` / ``GITFEATURES_TICKET_SEPERATOR``: Separator between the ticket id and
  the name. Default: the branch separator.
- ``gitfeatures.ticketPrefix`` / ``GITFEATURES_TICKET_PREFIX``: Prefix added to ticket ids that do not
  already have it (e.g. ``ENG-``).
- ``gitfeatures.requireTicketId`` / ``GITFEATURES_REQUIRE_TICKETID``: When true, ``git feature new``
  requires a ticket id. Default: ``false``.
- ``gitfeatures.debug`` / ``GITFEATURES_DEBUG``: When true, prints debug output. Default: ``false``.
- ``changelog.enabled`` / ``GITFEATURES_CHANGELOG_ENABLED``: When true, ``git feature new`` writes a
  changelog for the new branch, and ``git pullrequest`` uses it as the PR description. Default:
  ``false``. See `Changelogs`_.
- ``changelog.template`` / ``GITFEATURES_CHANGELOG_TEMPLATE``: Changelog template file. See
  `Changelog template`_.

The environment variables keep their original spelling (``SEPERATOR``) for compatibility.

These are environment variables only, because they are secrets or per-command switches that do not
belong in a committed file:

- ``GITHUB_TOKEN`` (or ``GH_TOKEN``): Lets ``git pullrequest`` create GitHub PRs through the API. See
  `git pullrequest`_.
- ``LINEAR_API_KEY`` (or ``LINEAR_TOKEN``): See `Linear integration`_.
- ``CONSOLEONLY``: If set, ``git pullrequest`` prints the PR URL instead of creating or opening the PR.

Migrating from environment variables
====================================

Earlier versions were configured only with environment variables, usually exported from a shell
profile. Those still work unchanged. To move a repo's settings into ``.gitfeatures``:

1. Write each exported value into the repo's ``.gitfeatures``, using the key from `Settings`_. For
   example, ``export GITFEATURES_TICKET_PREFIX=ENG-`` becomes:

   ::

       $ git config --file .gitfeatures gitfeatures.ticketPrefix ENG-

2. Commit ``.gitfeatures``.
3. Remove the ``export`` lines from your shell profile. While they remain, they win over
   ``.gitfeatures`` in every repo, and gitfeatures prints a notice wherever they disagree.

If your repo has a ``changelog-template.md`` at its root, it keeps working. To make it explicit, add
``changelog.template = changelog-template.md`` under ``[changelog]``.

********
Workflow
********

These scripts follow the `GitHub flow <https://docs.github.com/en/get-started/using-github/github-flow>`_:
each change is made on a short-lived branch created from the base branch, reviewed in a pull request,
merged, and then deleted. ``git release``, ``git stable`` and ``git hotfix`` add date-stamped branches
for teams that cut releases.

*****************
Command reference
*****************

git feature
===========

- ``git feature new <name> [<ticket_id>]``: Create and push a ``feature_<name>`` branch from the current
  branch. If ``<ticket_id>`` is given, the branch is ``feature_<ticket_id>_<name>``, using the configured
  separators and ticket prefix. You are asked to confirm if you are not on the base branch. If
  ``changelog.enabled`` is on, a changelog file is written for the branch (see `Changelogs`_).
- ``git feature finish [<name>]``: Delete the current feature branch (or the named one) locally and on
  origin. It refuses if the branch has commits that are not in ``origin/<base branch>``, so merge the PR
  first.

You can also pass a full branch path in the ``feature/ENG-123-description`` style that tools such as
Linear suggest. With this in ``.gitfeatures``:

::

    [gitfeatures]
        ticketSeparator = -
        ticketPrefix = ENG-

running ``git feature new feature/ENG-123-description`` creates ``feature/ENG-123-description``,
normalising the ticket id to ``ENG-123`` and keeping the hyphens and the slash.

git releasecandidate
====================

- ``git releasecandidate new [<name>]``: Same as ``git feature new`` with the ``releasecandidate``
  prefix. Without a name, today's date (``YYYY-MM-DD``) is used.
- ``git releasecandidate finish [<name>]``: Same as ``git feature finish``.

git release, git stable and git hotfix
======================================

These create and switch between date-stamped branches:

- ``git release new [<suffix>]``: Create and push ``release_YYYYMMDD_<suffix>`` from the current
  checkout. Without a suffix, the current time (``HHMMSS``) is used. If more than three release branches
  exist, you are asked whether to delete the oldest.
- ``git release``: Check out the latest ``release_YYYYMMDD…`` branch on origin.

``git stable`` and ``git hotfix`` work the same way with the ``stable`` and ``hotfix`` prefixes.

git pullrequest
===============

Opens a pull request from the current branch into the base branch:

1. Refuses to run on the base branch.
2. If the branch is behind ``origin/<base branch>``, offers to update it with a merge or a rebase (see
   ``gitfeatures.strategy``) and stops if there are conflicts for you to fix.
3. Offers to push unpushed commits.
4. Creates or opens the PR:

   - With ``GITHUB_TOKEN`` or ``GH_TOKEN`` set, on GitHub, it creates the PR through the API as a **draft**,
     titled with the branch name. If ``changelog.enabled`` is on and the branch's changelog file exists,
     the file becomes the PR description. It then opens the PR in your browser. If the API call fails,
     it falls back to the browser flow below.
   - Otherwise it opens the "new pull request" page for GitHub or Bitbucket in your browser.

``git pullrequest --dry-run``, or ``CONSOLEONLY=1``, prints the PR URL instead of creating or opening
anything.

git changelog
=============

Renders the changelog template for a branch without creating the branch, or sets up a template:

::

    $ git changelog                                  # print the changelog for the current branch
    $ git changelog --branch feature/ENG-123-change  # ... for another branch name
    $ git changelog --ticket ENG-123                 # ... with this ticket id (fetched from Linear if configured)
    $ git changelog --write                          # write it to changelog/<branch>.md
    $ git changelog --write --out /tmp/preview.md    # ... or to another file
    $ git changelog --init-template                  # copy the default template into the repo
    $ git changelog --init-template --out .github/changelog-template.md --force

``--init-template`` cannot be combined with ``--branch``, ``--ticket`` or ``--write``. See
`Changelog template`_.

**********
Changelogs
**********

When ``changelog.enabled`` is on, ``git feature new`` writes ``changelog/<branch>.md`` for the new
branch, leaving out the ``feature/`` prefix: ``feature/ENG-123-change`` gets
``changelog/ENG-123-change.md``. An existing file is not overwritten. The file is not committed for
you. Fill it in as you work and commit it with your changes. ``git pullrequest`` uses it as the PR
description when it creates the PR through the API.

Changelog template
==================

Changelogs are rendered with `Jinja2 <https://jinja.palletsprojects.com/>`_ from a template.
gitfeatures ships a default template
(`gitfeatures/templates/changelog-template.md <gitfeatures/templates/changelog-template.md>`_) with
Purpose, Background, Changes, Testing and Links sections. To use your own, copy the default into your
repository and edit it:

::

    $ git changelog --init-template
    Wrote /path/to/repo/changelog-template.md
    Set changelog.template = changelog-template.md in /path/to/repo/.gitfeatures
    Set changelog.enabled = true in /path/to/repo/.gitfeatures
    Edit the template, then commit it and .gitfeatures.

``--init-template`` writes the default template to ``changelog-template.md`` (or to ``--out <path>``,
relative to the top of the working tree, or wherever ``changelog.template`` already points) and records
the path as ``changelog.template`` in ``.gitfeatures``. If ``.gitfeatures`` does not already set
``changelog.enabled``, it sets it to ``true``. It will not overwrite an existing file unless you pass
``--force``.

The template is chosen in this order:

1. ``changelog.template`` (or ``GITFEATURES_CHANGELOG_TEMPLATE``). If that file does not exist,
   gitfeatures prints a warning and uses the bundled default.
2. ``changelog-template.md`` at the top of the working tree, for repos set up before
   ``changelog.template`` existed.
3. The bundled default.

Run ``git changelog`` after editing the template to see what a new branch will get. For example, to add
a rollout checklist to every changelog:

::

    ## Rollout
    - [ ] Feature flag created
    - [ ] Docs updated
    {% if ticket %}- [ ] {{ ticket }} moved to Done{% endif %}

Variables available to the template:

- ``branch``: the branch name.
- ``ticket``: the ticket id (e.g. ``ENG-123``), if one was given or found in the branch name.
- ``title``: the issue title if there is one, else the branch name.
- ``background``: the issue description, if there is one.
- ``changes``, ``testing``: ``"- "``, a starting bullet.
- ``repo_full_name``: ``owner/name`` from the ``origin`` URL, and ``repo_origin``: the URL itself. Both
  are empty if there is no ``origin``.
- ``master_branch``: the base branch.
- ``now``: the current UTC time, e.g. ``2026-01-31T09:30:00.000000Z``.
- ``issue``: the ticket in a provider-neutral form: ``provider``, ``id``, ``key``, ``title``,
  ``description``, ``url`` and the other fields below. Empty if there is no issue.
- ``linear``: the Linear issue, if one was fetched: ``identifier``, ``number``, ``title``,
  ``description``, ``url``, ``createdAt``, ``updatedAt``, ``priority``, ``estimate``,
  ``team`` (``key``, ``name``), ``state`` (``name``, ``type``), ``assignee`` (``name``,
  ``displayName``, ``email``) and ``labels`` (each with ``name``). Empty otherwise.

As in any Jinja2 template, a single trailing newline is dropped, and a variable that is not set renders
as an empty string. If the template cannot be read or rendered, the changelog is created empty. Set
``gitfeatures.debug`` to see why.

Linear integration
==================

If you track work in `Linear <https://linear.app>`_, gitfeatures can fill the changelog from the
ticket. Set ``LINEAR_API_KEY`` in your environment (never in ``.gitfeatures``), and give a ticket id in
either form:

::

    $ git feature new my_change 123                       # with ticketPrefix = ENG-, uses ENG-123
    $ git feature new feature/ENG-123-some-description    # see "git feature" above

If the issue is found, the template gets ``title``, ``background``, ``issue`` and ``linear`` from it
(the default template shows the ticket's details and links to it). If no key is set or the issue is not
found, the changelog is still created from the template without them. Only the team key and number
(``ENG`` and ``123``) are used to look the issue up.

***************
Troubleshooting
***************

``gitfeatures: GITFEATURES_… overrides … from …/.gitfeatures``
    An environment variable, usually exported from your shell profile, is overriding the repo's
    ``.gitfeatures``. Remove the export if the file should win. See
    `Migrating from environment variables`_.

``gitfeatures.core: unable to read …/.gitfeatures: fatal: bad config line …``
    ``.gitfeatures`` is not valid git config. Check it with ``git config --file .gitfeatures --list``.

``gitfeatures: changelog template … (set by …) does not exist, so the bundled default is used``
    ``changelog.template`` or ``GITFEATURES_CHANGELOG_TEMPLATE`` points at a missing file. The message
    names the setting that pointed there. Paths are relative to the top of the working tree.

``can't issue pull requests on <branch>``
    You are on the base branch. If that is not your base branch, set ``gitfeatures.masterBranch``.

``none zero exit status executing: git …``
    A git command failed, often because there is no ``origin`` remote or the branch does not exist on
    it. Run the git command shown to see git's own error.

To see what gitfeatures is doing, including which changelog template it uses, set
``gitfeatures.debug = true`` or run with ``GITFEATURES_DEBUG=1``.

***********
Development
***********

See `CONTRIBUTING.md <CONTRIBUTING.md>`_ for setting up a development environment, running the tests
and adding a setting.

*******
License
*******

MIT
