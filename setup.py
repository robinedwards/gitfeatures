from setuptools import setup

with open("README.rst", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gitfeatures",
    version="0.1.11",
    packages=["gitfeatures"],
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    python_requires=">=3.8",
    install_requires=[],
    entry_points={
        "console_scripts": [
            "git-feature=gitfeatures.core:cli_feature",
            "git-hotfix=gitfeatures.core:cli_hotfix",
            "git-release=gitfeatures.core:cli_release",
            "git-stable=gitfeatures.core:cli_stable",
            "git-pullrequest=gitfeatures.core:cli_pullrequest",
            "git-releasecandidate=gitfeatures.core:cli_releasecandidate",
        ]
    },
)
