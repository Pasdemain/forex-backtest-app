from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="forex-backtest-app",
    version="1.0.0",
    author="Pasdemain",
    description="A comprehensive forex backtesting application with news event analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Pasdemain/forex-backtest-app",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "forex-backtest=main:main",
        ],
    },
    include_package_data=True,
)
