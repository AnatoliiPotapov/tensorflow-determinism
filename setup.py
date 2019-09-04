import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="tfdeterminism",
    version="0.0.1",
    author="Anatoly Potapov (forked from NVIDIA)",
    author_email="anatolii.s.potapov@gmail.com",
    description="Make tensorflow reproducible",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AnatoliiPotapov/tensorflow-determinism",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2.0",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)