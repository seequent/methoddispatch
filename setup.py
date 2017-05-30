# -*- coding: utf-8 -*-
import setuptools

import methoddispatch


setuptools.setup(
    name="methoddispatch",
    version="1.1.0",
    author="ARANZ Geo",
    author_email="tim.mitchell@aranzgeo.com",
    description="singledispatch decorator for functions and instance methods.",
    license="BSD",
    keywords="single dispatch decorator method",
    url="https://github.com/aranzgeo/methoddispatch",
    packages=setuptools.find_packages(),
    long_description=methoddispatch.__doc__,
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: BSD License",
    ],
)
