"""Setup script for Company Assistant Agent."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="company-assistant-agent",
    version="0.1.0",
    author="ZURU Melon",
    description="AI-powered company assistant system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "python-dotenv>=1.0.0",
        "typer>=0.9.0",
        "rich>=13.7.0",
        "zhipuai>=2.1.5.20250726",
        "httpx>=0.26.0",
        "chromadb>=0.4.22",
        "sentence-transformers>=2.3.1",
        "markdown>=3.5.1",
        "duckduckgo-search>=4.1.1",
    ],
    entry_points={
        "console_scripts": [
            "company-assistant=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
