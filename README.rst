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

This project works out of the box with github. If you would like to use bitbucket set the following environment variable

    $ export GITFEATURES_REPO='bitbucket'

This project defaults to using 'main' for the base branch. If you would like to configure a different base branch set the following environment variable

    $ export GITFEATURES_MASTER_BRANCH='develop'

This project defaults to using 'merge' strategy for pre-PR automation. If you would like to configure a rebase strategy set the following envronment variable

    $ export GITFEATURES_STRATEGY='rebase'

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

You can also pass a full branch path in the popular ``feature/ENG-123-description`` style. Set:

::

    export GITFEATURES_TICKET_SEPERATOR=-
    export GITFEATURES_TICKET_PREFIX=ENG-

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

************************
Environment variables
************************

- ``GITFEATURES_REPO``: ``github`` (default) or ``bitbucket``.
- ``GITFEATURES_MASTER_BRANCH``: Base branch name. Default: ``main``.
- ``GITFEATURES_STRATEGY``: ``merge`` (default) or ``rebase``.
- ``GITFEATURES_FORK_PR_STRATEGY``: If set to ``private`` on GitHub, uses the compare view instead of the new-PR shortcut.
- ``GITFEATURES_BRANCH_SEPERATOR``: Separator used between parts of branch names. Default: ``_``.
- ``GITFEATURES_TICKET_SEPERATOR``: Separator between ticket id and name. Default: same as ``GITFEATURES_BRANCH_SEPERATOR``.
- ``GITFEATURES_TICKET_PREFIX``: Optional enforced prefix for ticket ids (e.g. ``PROJ-``).
- ``GITFEATURES_REQUIRE_TICKETID``: Set to ``true`` to require a ticket id on ``feature new``/``hotfix new``.
- ``CONSOLEONLY``: If set, print PR URL instead of opening a browser.
- ``GITHUB_TOKEN``: If set, PRs are created via the GitHub API instead of opening the browser. When present, if ``./changelog/<branch>.md`` exists, its contents are used as the PR description.
- ``GITFEATURES_CHANGELOG_ENABLED``: When set to ``true`` (or ``1/yes/on``), enables changelog generation on ``git feature new`` and PR body population from the changelog on ``git pullrequest``. Default: ``false``.

Changelog files
===============

When ``GITFEATURES_CHANGELOG_ENABLED`` is enabled and you run ``git feature new <name>``, a ``./changelog/<rest-of-branch>.md`` file is created for the new branch if it does not already exist (the leading ``feature/`` is omitted from the filename). When creating a PR (``git pullrequest``), if the flag is enabled, a changelog file exists for the current branch, and ``GITHUB_TOKEN`` is set, its contents become the PR body.

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

    If you configure ``GITFEATURES_TICKET_PREFIX='ENG-'``, the tool will use ``ENG-123`` as the Linear identifier.
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

- Default path: ``changelog-template.md`` in the repo root
- If missing, falls back to a bundled default inside the ``gitfeatures`` package (``gitfeatures/templates/changelog-template.md``).
- Override with: ``GITFEATURES_CHANGELOG_TEMPLATE`` (absolute or repo-root-relative)
- Variables available to the template:
  - ``branch``: new branch name
  - ``ticket``: detected ticket identifier (e.g. ``ENG-123``) if available
  - ``repo_full_name``: owner/name derived from ``origin`` url
  - ``master_branch``: base branch (default: ``main``)
  - ``linear``: dict with ``identifier``, ``title``, ``description``, ``url`` (if available)
  - ``issue``: generic issue dict for providers (``provider``, ``id``, ``key``, ``title``, ``description``, ``url``)
  - ``title``, ``background``, ``changes``, ``testing``: prefilled suggestions (title/background come from Linear if available)
  - ``now``: current UTC timestamp in ISO format
- If the template is missing, the tool falls back to a bundled default inside the package. If rendering fails, the changelog is created empty.

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

- Ticket handling: if ``GITFEATURES_TICKET_PREFIX`` is set and the provided ticket id does not start with it, the prefix is preprended automatically.
- Branch existence checks protect against creating duplicates (local or remote).
- ``git release``/``git stable`` detect the latest remote branch by date-based naming and check it out.

********
Development
********

::

    $ pip install -r requirements-dev.txt
    $ pip install -e .

********
License
********

MIT
