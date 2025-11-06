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
