"""Package setup"""
import setuptools


with open("README.md", "r") as f:
    long_description = f.read()

requirements = ["typer", "rich", "shellingham", "requests"]


setuptools.setup(
    name="forksearch",
    version="0.0.1",
    author="David Brumley",
    description="Collect and explore forks and stars for a github repository.",
    packages=setuptools.find_packages(
        exclude=["dist", "build", "*.egg-info", "tests"]
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "forksearch = forksearch.main:main"
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
)
