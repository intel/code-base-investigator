#!/usr/bin/env python3
# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup

setup(
    name="codebasin",
    version="1.1.1",
    description="Code Base Investigator",
    author="John Pennycook",
    author_email="john.pennycook@intel.com",
    url="https://www.github.com/intel/code-base-investigator",
    packages=["codebasin", "codebasin.schema", "codebasin.walkers"],
    include_package_data=True,
    scripts=["bin/codebasin", "bin/cbicov"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development",
    ],
    python_requires=">=3.12",
    install_requires=[
        "numpy==1.26.0",
        "matplotlib==3.8.2",
        "pathspec==0.12.1",
        "pyyaml==6.0.1",
        "scipy==1.12.0",
        "jsonschema==4.21.1",
    ],
)
