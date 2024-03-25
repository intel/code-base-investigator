Code Base Investigator
======================

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Introduction

   Getting Started <self>
   specialization
   features

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Tutorial

   sample-code-base
   compilation-databases
   analysis
   excluding-files
   emulating-compiler-behavior

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Reference

   cmd

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Contributing

   How to Contribute <https://github.com/intel/code-base-investigator/blob/main/CONTRIBUTING.md>
   GitHub <https://github.com/intel/code-base-investigator>
   notices-and-disclaimers


Code Base Investigator (CBI) is an analysis tool that provides insight into the
portability and maintainability of an application's source code.

- Measure ":doc:`code divergence <specialization>`" to understand how much code
  is *specialized* for different compilers, operating systems, hardware
  micro-architectures and more.

- Visualize the distance between the code paths used to support different
  compilation targets.

- Identify stale, legacy, code paths that are unused by any compilation target.

- Export metrics and code path information required for P3 analysis using
  `other tools`_.

.. _other tools: https://intel.github.io/p3-analysis-library/index.html


Installation
############

The latest release of CBI is version 1.2.0. To download and install this
release, run the following::

    $ git clone --branch 1.2.0 https://github.com/intel/code-base-investigator.git
    $ cd code-base-investigator
    $ pip install .

We strongly recommend installing CBI within a `virtual environment`_.

.. _`virtual environment`: https://docs.python.org/3/library/venv.html


Getting Started
###############

Using CBI to analyze a code base is a three step process. For more detailed
information on any of these steps, we recommend that you work through the
tutorial using the :doc:`sample code base<sample-code-base>`.


1. **Generate a compilation database for each platform**

   You can use the |CMAKE_EXPORT_COMPILE_COMMANDS option|_ with `CMake`_,
   intercept the compilation of an application using `Bear`_, or write a
   database manually.

   .. _`CMake`: https://cmake.org/
   .. _`Bear`: https://github.com/rizsotto/Bear

.. |CMAKE_EXPORT_COMPILE_COMMANDS option| replace:: :code:`CMAKE_EXPORT_COMPILE_COMMANDS` option
.. _CMAKE_EXPORT_COMPILE_COMMANDS option: https://cmake.org/cmake/help/latest/variable/CMAKE_EXPORT_COMPILE_COMMANDS.html


2. **Create a TOML file describing the analysis**

   CBI reads platform definitions from a `TOML`_ file, like the one shown
   below:

   .. code:: toml

       [platform.cpu]
       commands = "cpu/compile_commands.json"

       [platform.gpu]
       commands = "gpu/compile_commands.json"

   .. _`TOML`: https://toml.io/en/


3. **Launch CBI**

   To perform a full analysis, launch ``codebasin`` with no arguments except
   the input TOML file:

   .. code:: text

       $ codebasin analysis.toml

   To see the other options that are available, run ``codebasin -h``.
