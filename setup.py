"""Setup script for localization-analyzer.

NOT: Bu dosya geriye dönük uyumluluk için korunmaktadır.
Birincil yapılandırma pyproject.toml dosyasındadır.
"""

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
    author_email="sezginpak@gmail.com",
    description=version_info["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/sezginpak/localization-analyzer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Localization",
        "Topic :: Software Development :: Internationalization",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
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
        "certifi>=2023.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "black>=23.0",
            "flake8>=6.0",
            "build>=1.0",
            "twine>=4.0",
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
            "templates/*.yml",
        ],
    },
    keywords="localization i18n internationalization swift ios strings translation cli",
    project_urls={
        "Homepage": "https://github.com/sezginpak/localization-analyzer",
        "Documentation": "https://github.com/sezginpak/localization-analyzer#readme",
        "Repository": "https://github.com/sezginpak/localization-analyzer",
        "Bug Tracker": "https://github.com/sezginpak/localization-analyzer/issues",
        "Changelog": "https://github.com/sezginpak/localization-analyzer/blob/main/CHANGELOG.md",
    },
)
