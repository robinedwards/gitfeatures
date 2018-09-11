from setuptools import setup

long_description = ""
try:
    long_description = open("README.rst", "rb").read()
except:
    pass


setup(
    name="gitfeatures",
    version="0.0.5",
    packages=['gitfeatures'],
    license="MIT",
    long_description=long_description,
    use_2to3=True,
    scripts=[
        'scripts/git-feature',
        'scripts/git-hotfix',
        'scripts/git-stable',
        'scripts/git-pullrequest',
        'scripts/git-releasecandidate'
    ]
)
