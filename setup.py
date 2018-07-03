# -*- coding: utf-8 -*-
import setuptools

import methoddispatch


setuptools.setup(
    name="methoddispatch",
    version=methoddispatch.__version__,
    author=methoddispatch.__author__,
    author_email="tim.mitchell@seequent.com",
    description="singledispatch decorator for functions and methods.",
    license=methoddispatch.__license__,
    keywords="single dispatch decorator method",
    url="https://github.com/seequent/methoddispatch",
    packages=setuptools.find_packages(),
    long_description=open('README.rst').read(),
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: BSD License",
    ],
)
