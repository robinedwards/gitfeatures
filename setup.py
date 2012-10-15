from setuptools import setup

long_description = ""
try:
    long_description = open("README.rst", "rb").read()
except:
    pass


setup(
    name="gitfeatures",
    version="0.0.2",
    packages=['gitfeatures'],
    license="MIT",
    long_description=long_description,
    scripts=['scripts/git-feature', 'scripts/git-hotfix', 'scripts/git-pullrequest']
)
