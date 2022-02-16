from setuptools import setup

readme = open("README.rst").read()
long_description = readme

setup(
    name="gitfeatures",
    version="0.0.6",
    packages=["gitfeatures"],
    license="MIT",
    long_description=long_description,
    install_requires=["six"],
    scripts=[
        "scripts/git-feature",
        "scripts/git-hotfix",
        "scripts/git-stable",
        "scripts/git-pullrequest",
        "scripts/git-releasecandidate",
    ],
)
