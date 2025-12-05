"""Setup script for localization-analyzer."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read version
version_file = Path(__file__).parent / "localization_analyzer" / "__version__.py"
version_info = {}
exec(version_file.read_text(), version_info)

setup(
    name="localization-analyzer",
    version=version_info["__version__"],
    author=version_info["__author__"],
    description=version_info["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/localization-analyzer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Localization",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
        "watch": [
            "watchdog>=3.0",
        ],
        "progress": [
            "tqdm>=4.65",
        ],
    },
    entry_points={
        "console_scripts": [
            "localization-analyzer=localization_analyzer.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "localization_analyzer": [
            "templates/*",
        ],
    },
    keywords="localization i18n l10n translation swift ios react flutter android",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/localization-analyzer/issues",
        "Source": "https://github.com/yourusername/localization-analyzer",
        "Documentation": "https://github.com/yourusername/localization-analyzer#readme",
    },
)
