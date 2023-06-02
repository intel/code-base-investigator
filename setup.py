#!/usr/bin/env python3
# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

from setuptools import setup

setup(name='codebasin',
      version='1.05',
      description='Code Base Investigator',
      author='John Pennycook',
      author_email='john.pennycook@intel.com',
      url='https://www.github.com/intel/code-base-investigator',
      packages=['codebasin'],
      scripts=['codebasin.py'],
      classifiers=['Development Status :: 3 - Alpha',
                   'Environment :: Console',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Programming Language :: Python',
                   'Topic :: Software Development'],
      python_requires='>=3.6',
      install_requires=['numpy',
                        'matplotlib',
                        'pyyaml',
                        'scipy',
                        'jsonschema']
      )
