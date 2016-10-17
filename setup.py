# -*- coding: utf-8 -*-
import setuptools

import methoddispatch


setuptools.setup(
    name = "methoddispatch",
    version = "1.0.3",
    author = "Tim Mitchell",
    author_email = "tim.mitchell@leapfrog3d.com",
    description = "singledispatch decorator for functions and instance methods.",
    license = "BSD",
    keywords = "single dispatch decorator method",
    url = "https://github.com/tim-mitchell/methoddispatch",
    packages = setuptools.find_packages(),
    long_description=methoddispatch.__doc__,
    classifiers=[
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: BSD License",
    ],
)
