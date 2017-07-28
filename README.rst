===========
git features
===========

git helper scripts for managing feature branches and issuing pull requests

************
Installation
************

    $ pip install git+git://github.com/robinedwards/gitfeatures.git

Install for development:

    $ git clone git://github.com/robinedwards/gitfeatures.git
    $ cd gitfeatures
    $ python setup.py develop

**********
Background
**********

These scripts are designed to follow the github git work flow http://scottchacon.com/2011/08/31/github-flow.html

********
Features
********

Create a new feature (create a new local and remote branch prefixed 'feature_')

    $ git feature new html_pruning

Issue pull request for the current branch (to be reviewed by someone else).

    $ git pullrequest

After pull request has been excepted and merged into master finish the feature (delete local and remote branch)

    $ git feature finish

Or if your not currently working on the feature branch

    $ git feature finish html_pruning

Or if you wish to create a stable branch from a specific checkout

    $ git stable

will create a branch called stable_YYYYMMDD

*********
Hot fixes
*********

For bugs and hot fixes the same functionality is used with 'hotfix' instead of 'feature'

    $ git hotfix ie7_menu
    ...
    $ git hotfix finish
