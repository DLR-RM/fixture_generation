import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="fixture_generation",
    version="0.1.0",
    author="Wout Boerdijk",
    author_email="wout.boerdijk@dlr.de",
    description="fixture_generation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/DLR-RM/fixture_generation",
    packages=setuptools.find_packages(exclude=['fixture_files']),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
