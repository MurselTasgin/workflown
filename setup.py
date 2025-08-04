#!/usr/bin/env python3
"""
Setup script for workflown package
"""

from setuptools import setup, find_packages
import os

# Read the README file for long description
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements from requirements.txt if it exists
def read_requirements():
    requirements = []
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r", encoding="utf-8") as fh:
            requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]
    return requirements

setup(
    name="workflown",
    version="0.1.0",
    author="Workflown Team",
    author_email="contact@workflown.dev",
    description="A modular workflow execution framework with pluggable components",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/murseltasgin/workflown/workflown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "myst-parser>=0.18.0",
        ],
        "examples": [
            "requests>=2.28.0",
            "beautifulsoup4>=4.11.0",
            "aiohttp>=3.8.0",
            "asyncio-throttle>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "workflown=workflown.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="workflow, automation, task execution, distributed computing, async",
    project_urls={
        "Bug Reports": "https://github.com/murseltasgin/workflown/workflown/issues",
        "Source": "https://github.com/murseltasgin/workflown/workflown",
        "Documentation": "https://workflown.readthedocs.io/",
    },
) 