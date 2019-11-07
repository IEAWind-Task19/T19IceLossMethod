import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="t19_ice_loss", # Replace with your own username
    version="2.2.2",
    author="IEA Wind Task 19",
    author_email="timo.karlsson@vtt.fi",
    description="A tool to estimate icing losses from wind turbine SCADA data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/IEAWind-Task19/IceLossMethod",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)