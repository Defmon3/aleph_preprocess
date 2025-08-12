from setuptools import setup, find_packages

setup(
    name="sanitize",
    version="0.0.1",
    author="Organized Crime and Corruption Reporting Project",
    packages=find_packages(exclude=["tests"]),
    package_dir={"sanitize": "sanitize"},
    include_package_data=True,
    install_requires=[
        # When you use this in production, pin the dependencies!
        "followthemoney",
        "followthemoney-store[postgresql]",
        "servicelayer[google,amazon]",
        "beautifulsoup4>=4.13.4",
        "lxml>=6.0.0",
        "loguru>=0.7.3",
        "click>=8.2.1",

    ],
    license="MIT",
    zip_safe=False,
    test_suite="tests",
    tests_require=[],
    entry_points={
        "console_scripts": ["sanitize = sanitize.cli:sanitize"],

    },
)