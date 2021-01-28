from setuptools import setup

long_description = ""
try:
    long_description = open("README.rst", "r").read()
except:
    pass


setup(
    name="gitfeatures",
    version="0.0.6",
    packages=['gitfeatures'],
    license="MIT",
    long_description=long_description,
    install_requires=[
        'six'
    ],
    scripts=[
        'scripts/git-feature',
        'scripts/git-hotfix',
        'scripts/git-stable',
        'scripts/git-pullrequest',
        'scripts/git-releasecandidate'
    ]
)
