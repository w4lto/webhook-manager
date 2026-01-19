#!/usr/bin/env python3
"""
Setup configuration for webhook-tunnel
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name="webhook-tunnel",
    version="1.0.0",
    author="Webhook Tunnel Contributors",
    author_email="contact@example.com",
    description="🚇 Expose local ports with custom DNS for webhook testing - K9s-style TUI interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/webhook-tunnel",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/webhook-tunnel/issues",
        "Documentation": "https://github.com/yourusername/webhook-tunnel#readme",
        "Source Code": "https://github.com/yourusername/webhook-tunnel",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Framework :: AsyncIO",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.1.0",
        "textual>=0.47.0",
        "rich>=13.0.0",
        "psutil>=5.9.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "webhook-server": [
            "flask>=3.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tunnel=webhook_tunnel.cli:main",
            "tunnel-tui=webhook_tunnel.tui:main",
            "tunnel-server=webhook_tunnel.webhook_server:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords=[
        "webhook",
        "tunnel",
        "ngrok",
        "localhost",
        "development",
        "testing",
        "port-forwarding",
        "dns",
        "tui",
        "k9s",
    ],
)
