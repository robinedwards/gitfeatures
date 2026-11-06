============
git features
============

git helper scripts for managing feature branches and issuing pull requests

************
Installation
************

::

    $ pip install git+https://github.com/robinedwards/gitfeatures.git

Install for development:

::

    $ git clone https://github.com/robinedwards/gitfeatures.git
    $ cd gitfeatures
    $ pip install -r requirements-dev.txt
    $ pre-commit install
    $ pip install -e .

*************
Configuration
*************

This project works out of the box with github and a ``main`` base branch. To configure it for a
repository, commit a ``.gitfeatures`` file to the root of that repository, so everyone who works on
it gets the same settings:

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

The file uses git's own config format (the same as ``.git/config``) and is read with
``git config --file .gitfeatures``. Key names are case-insensitive, and a key written without a value
(``requireTicketId`` on its own line) means ``true``. You can edit it by hand or with git:

::

    $ git config --file .gitfeatures gitfeatures.masterBranch develop

Every setting can also be set with an environment variable, as before. An environment variable wins
over the ``.gitfeatures`` file, which wins over the default. When an environment variable overrides
a different value from the file, gitfeatures prints a notice saying so. This lets you override a
setting for one command, for example ``GITFEATURES_MASTER_BRANCH=release git pullrequest``.

See `Settings`_ for every key and environment variable.

**********
Background
**********

These scripts are designed to follow the github git work flow http://scottchacon.com/2011/08/31/github-flow.html

********
Features
********

Create a new feature (create a new local and remote branch prefixed 'feature')

    $ git feature new html_pruning

Issue pull request for the current branch (to be reviewed by someone else).

    $ git pullrequest

After pull request has been accepted and merged into main finish the feature (delete local and remote branch)

    $ git feature finish

Or if your not currently working on the feature branch

    $ git feature finish html_pruning

Or if you wish to create a stable branch from a specific checkout

    $ git stable|hotfix|release new

will create a branch called stable|hotfix|release_YYYYMMDD

Or if you wish to switch to the current latest stable|hotfix|release branch

    $ git stable|hotfix|release

*********
Hot fixes
*********

For bugs and hot fixes the same functionality is used with 'hotfix' instead of 'feature'

    $ git hotfix ie7_menu
    ...
    $ git hotfix finish

***********************
Full command reference
***********************

``git feature``
===============

- ``git feature new <name> [<ticket_id>]``: Create and push a new ``feature_<name>`` branch. If ``<ticket_id>`` is provided, the branch becomes ``feature_<ticket>_<name>`` (see separators below).
- ``git feature finish [<name>]``: Delete the current feature branch (or the named one) both locally and on origin, after it has been merged into the base branch.

Linear-style input (e.g. Linear.app)
------------------------------------

You can also pass a full branch path in the popular ``feature/ENG-123-description`` style. Set this in ``.gitfeatures``:

::

    [gitfeatures]
        ticketSeparator = -
        ticketPrefix = ENG-

(or ``GITFEATURES_TICKET_SEPERATOR=-`` and ``GITFEATURES_TICKET_PREFIX=ENG-`` in the environment).

Then run:

::

    $ git feature new feature/ENG-123-description

This will normalize the ticket id to ``ENG-123`` and preserve hyphens and the slash.

``git hotfix``
==============

- ``git hotfix new <name> [<ticket_id>]``: Same as feature, but with ``hotfix`` prefix.
- ``git hotfix finish [<name>]``: Same as feature finish.

``git release`` / ``git stable``
================================

- ``git release new [<suffix>]``: Create and push a new branch named ``release_YYYYMMDD_<suffix>``. If ``<suffix>`` is omitted, current time (``HHMMSS``) is used as the suffix.
- ``git release``: Check out the latest remote release branch.
- ``git stable new [<suffix>]`` and ``git stable`` behave the same for ``stable``.

Notes:

- If more than 3 branches exist of that type, you'll be prompted to delete the oldest one.

``git pullrequest``
===================

Validates your branch and opens your browser to the correct PR creation URL.

- Ensures you are not on the base branch.
- If your branch is behind ``origin/<base>``, offers to update by merge or rebase (configurable) and guides you through conflicts if they occur.
- Prompts to push unpushed commits.
- Opens the PR page for GitHub or Bitbucket. Set ``CONSOLEONLY=1`` to print the URL only.

********
Settings
********

Each setting can be given in the repository's ``.gitfeatures`` file or as an environment variable.
The environment variable wins.

- ``gitfeatures.repo`` / ``GITFEATURES_REPO``: ``github`` (default) or ``bitbucket``.
- ``gitfeatures.masterBranch`` / ``GITFEATURES_MASTER_BRANCH``: Base branch name. Default: ``main``.
- ``gitfeatures.strategy`` / ``GITFEATURES_STRATEGY``: ``merge`` (default) or ``rebase``.
- ``gitfeatures.forkPrStrategy`` / ``GITFEATURES_FORK_PR_STRATEGY``: If set to ``private`` on GitHub, uses the compare view instead of the new-PR shortcut.
- ``gitfeatures.branchSeparator`` / ``GITFEATURES_BRANCH_SEPERATOR``: Separator used between parts of branch names. Default: ``_``.
- ``gitfeatures.ticketSeparator`` / ``GITFEATURES_TICKET_SEPERATOR``: Separator between ticket id and name. Default: same as the branch separator.
- ``gitfeatures.ticketPrefix`` / ``GITFEATURES_TICKET_PREFIX``: Optional enforced prefix for ticket ids (e.g. ``PROJ-``).
- ``gitfeatures.requireTicketId`` / ``GITFEATURES_REQUIRE_TICKETID``: Set to ``true`` to require a ticket id on ``feature new``/``hotfix new``.
- ``gitfeatures.debug`` / ``GITFEATURES_DEBUG``: Set to ``true`` to print debug output.
- ``changelog.enabled`` / ``GITFEATURES_CHANGELOG_ENABLED``: When ``true``, enables changelog generation on ``git feature new`` and PR body population from the changelog on ``git pullrequest``. Default: ``false``.
- ``changelog.template`` / ``GITFEATURES_CHANGELOG_TEMPLATE``: Changelog template file, absolute or relative to the repo root. See `Changelog template`_.

Boolean settings accept ``true``, ``1``, ``yes`` or ``on``.

These are environment variables only, because they are secrets or per-invocation switches that do not
belong in a committed file:

- ``CONSOLEONLY``: If set, print PR URL instead of opening a browser.
- ``GITHUB_TOKEN`` (or ``GH_TOKEN``): If set, PRs are created via the GitHub API instead of opening the browser. When present, if ``./changelog/<branch>.md`` exists, its contents are used as the PR description.
- ``LINEAR_API_KEY`` (or ``LINEAR_TOKEN``): See `Linear integration (optional)`_.

Changelog files
===============

When ``changelog.enabled`` (or ``GITFEATURES_CHANGELOG_ENABLED``) is on and you run ``git feature new <name>``, a ``./changelog/<rest-of-branch>.md`` file is created for the new branch if it does not already exist (the leading ``feature/`` is omitted from the filename). When creating a PR (``git pullrequest``), if the flag is enabled, a changelog file exists for the current branch, and ``GITHUB_TOKEN`` is set, its contents become the PR body.

Linear integration (optional)
=============================

If you track work in Linear and your branch/ticket ids look like ``TEAM-123`` (e.g. ``ENG-123``), you can have the changelog file prefilled with the ticket's title and description.

Setup:

- **Set your Linear API key**:

  ::

      export LINEAR_API_KEY=your_linear_api_key

- **Provide a ticket id**:
  - Either pass it as the third argument to ``git feature new`` when your config requires ticket ids:

    ::

        git feature new my_change 123

    If you configure ``ticketPrefix = ENG-`` (or ``GITFEATURES_TICKET_PREFIX='ENG-'``), the tool will use ``ENG-123`` as the Linear identifier.

  - Or embed it in the name using the long form:

    ::

        git feature new feature/ENG-123-some-description

Behavior:

- On ``git feature new``, if ``LINEAR_API_KEY`` is set and a ticket id like ``ENG-123`` can be detected (either from the argument or the branch name), the tool fetches the issue from Linear and pre-populates ``./changelog/<branch>.md``:
  - Purpose: set from the Linear issue title
  - Background: first part of the Linear description
  - Links: includes the Linear issue URL

Notes:

- Only the team key and issue number are used (e.g. ``ENG`` and ``123``).
- If no Linear token is set or the issue is not found, the changelog is still created with a simple template so you can fill it in manually.

Templating via Jinja2
=====================

- On ``git feature new`` your changelog is rendered with **Jinja2** from a template file.

Changelog template
------------------

gitfeatures ships a default changelog template
(`gitfeatures/templates/changelog-template.md <gitfeatures/templates/changelog-template.md>`_).
To use your own, copy the default into your repository and edit it:

::

    $ git changelog --init-template
    Wrote /path/to/repo/changelog-template.md
    Set changelog.template = changelog-template.md in /path/to/repo/.gitfeatures
    Set changelog.enabled = true in /path/to/repo/.gitfeatures

This writes the default template to ``changelog-template.md`` in the repo root (or to ``--out <path>``,
relative to the repo root), and records it in ``.gitfeatures``. It also turns changelogs on if
``.gitfeatures`` does not already say whether they are on. It will not overwrite an existing file
unless you pass ``--force``. Commit the template and ``.gitfeatures`` so everyone on the repo uses them:

::

    [changelog]
        enabled = true
        template = .github/changelog-template.md

The template is chosen in this order:

1. ``changelog.template`` in ``.gitfeatures``, or ``GITFEATURES_CHANGELOG_TEMPLATE``: absolute, or relative
   to the repo root. If the file does not exist, gitfeatures says so and uses the bundled default.
2. ``changelog-template.md`` in the repo root, for repos that relied on it before ``changelog.template``
   existed.
3. The bundled default.

Variables available to the template:

- ``branch``: new branch name
- ``ticket``: detected ticket identifier (e.g. ``ENG-123``) if available
- ``repo_full_name``: owner/name derived from ``origin`` url
- ``master_branch``: base branch (default: ``main``)
- ``linear``: dict with ``identifier``, ``title``, ``description``, ``url`` (if available)
- ``issue``: generic issue dict for providers (``provider``, ``id``, ``key``, ``title``, ``description``, ``url``)
- ``title``, ``background``, ``changes``, ``testing``: prefilled suggestions (title/background come from Linear if available)
- ``now``: current UTC timestamp in ISO format

If rendering fails, the changelog is created empty.

Preview without creating a feature
----------------------------------

You can render or write the changelog for the current or a specific branch without creating a feature:

::

  # Preview to stdout for the current branch
  git changelog

  # Preview for a specific branch name
  git changelog --branch feature/ENG-123-awesome-change

  # Provide/override the ticket id
  git changelog --ticket ENG-123

  # Write to file (defaults to changelog/<branch>.md) or specify a path
  git changelog --write
  git changelog --write --out /tmp/preview.md

Behavior details
================

- Ticket handling: if the ticket prefix is set and the provided ticket id does not start with it, the prefix is preprended automatically.
- Branch existence checks protect against creating duplicates (local or remote).
- ``git release``/``git stable`` detect the latest remote branch by date-based naming and check it out.

***********
Development
***********

::

    $ pip install -r requirements-dev.txt
    $ pip install -e .

Run the tests with:

::

    $ pytest

The tests create throwaway git repos (with a local bare repo as ``origin``) in a temp directory and
ignore your own git config and ``GITFEATURES_*`` environment variables.

********
License
********

MIT
