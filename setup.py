# -*- coding: utf-8 -*-
import setuptools

import methoddispatch


setuptools.setup(
    name="methoddispatch",
    version=methoddispatch.__version__,
    author=methoddispatch.__author__,
    author_email="tim.mitchell@seequent.com",
    description="singledispatch decorator for class methods.",
    license=methoddispatch.__license__,
    keywords="single dispatch decorator method",
    url="https://github.com/seequent/methoddispatch",
    packages=setuptools.find_packages(),
    long_description=open('README.rst').read(),
    long_description_content_type="text/x-rst",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: BSD License",
    ],
)
