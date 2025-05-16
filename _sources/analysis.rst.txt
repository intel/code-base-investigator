Performing Analysis
===================

The main interface of CBI is the ``codebasin`` script, which can be invoked to
analyze a code base and produce various reports. Although CBI ships with other
interfaces specialized for certain use-cases, ``codebasin`` supports an
end-to-end workflow that should be preferred for general usage.

The simplest way to invoke ``codebasin`` is as shown below::

    $ codebasin analysis.toml

...but what is ``analysis.toml``? We need to use this file to tell CBI which
files are part of the code base, and where it should look to find the
compilation databases defining our platforms.

.. note::

    The TOML file can have any name, but we'll use "analysis.toml" throughout
    this tutorial.


Defining Platforms
##################

Each platform definition is a TOML `table`_, of the form shown below:

.. _`table`: https://toml.io/en/v1.0.0#table

.. code-block:: toml

    [platform.name]
    commands = "/path/to/compile_commands.json"

The table's name is the name of the platform, and we can use any meaningful
string. The ``commands`` key tells CBI where to find the compilation database
for this platform.

.. important::

    By default, ``codebasin`` searches the current working directory for source
    files to include in its analysis. Since we'll be running in the ``src``
    directory, we need to specify the ``commands`` paths relative to the
    ``src`` directory or as absolute paths.

In our example, we have two platforms that we're calling "cpu" and "gpu",
and our build directories are called ``build-cpu`` and ``build-gpu``, so
our platform definitions should look like this:

.. code-block:: toml

    [platform.cpu]
    commands = "../build-cpu/compile_commands.json"

    [platform.gpu]
    commands = "../build-gpu/compile_commands.json"

.. warning::
    Platform names are case sensitive! The names "cpu" and "CPU" would refer to
    two different platforms.


Running ``codebasin``
#####################

Running ``codebasin`` in the ``src`` directory with this analysis file gives
the following output:

.. code-block:: text
   :emphasize-lines: 4,5,6,7,9

    -----------------------
    Platform Set LOC % LOC
    -----------------------
              {}   2  6.06
           {cpu}   7 21.21
           {gpu}   7 21.21
      {cpu, gpu}  17 51.52
    -----------------------
    Code Divergence: 0.45
    Coverage (%): 93.94
    Avg. Coverage (%): 72.73

    Distance Matrix
    --------------
         cpu  gpu
    --------------
    cpu 0.00 0.45
    gpu 0.45 0.00

The results show that there are 2 lines of code that are unused by any
platform, 7 lines of code used only by the CPU compilation, 7 lines of code
used only by the GPU compilation, and 17 lines of code shared by both
platforms. Plugging these numbers into the equation for code divergence gives
0.45.

.. caution::
    If we had run ``codebasin`` in the parent directory, everything in the
    ``src``, ``build-cpu`` and ``build-gpu`` directories would have been
    included in the analysis. For our sample code base, this would have
    resulted in over 2000 lines of code being identified as unused! Why so
    many? CMake generates multiple ``*.cpp`` files, which it uses as part of
    the build process. ``codebasin`` will analyze such files unless we tell it
    not to (more on that later).


Running ``cbi-tree``
####################

Running ``codebasin`` provides an overview of divergence and coverage, which
can be useful when we want to familiarize ourselves with a new code base,
compare the impact of different code structures upon certain metrics, or track
specialization metrics over time. However, it doesn't provide any *actionable*
insight into how to improve a code base.

To understand how much specialization exists in each source file, we can
substitute ``codebasin`` for ``cbi-tree``::

    $ cbi-tree analysis.toml

This command performs the same analysis as ``codebasin``, but produces a tree
annotated with information about which files contain specialization:

.. code-block:: text
   :emphasize-lines: 8,9,11,16

    Legend:
    A: cpu
    B: gpu

    Columns:
    [Platforms | SLOC | Coverage (%) | Avg. Coverage (%)]

    [AB | 33 |  93.94 |  72.73] o /home/username/code-base-investigator/docs/sample-code-base/src/
    [AB | 13 | 100.00 |  92.31] ├── main.cpp
    [A- |  7 |  85.71 |  42.86] ├─o cpu/
    [A- |  7 |  85.71 |  42.86] │ └── foo.cpp
    [AB |  6 | 100.00 | 100.00] ├─o third-party/
    [AB |  1 | 100.00 | 100.00] │ ├── library.h
    [AB |  5 | 100.00 | 100.00] │ └── library.cpp
    [-B |  7 |  85.71 |  42.86] └─o gpu/
    [-B |  7 |  85.71 |  42.86]   └── foo.cpp

.. tip::

    Running ``cbi-tree`` in a modern terminal environment producers colored
    output to improve usability for large code bases.

Each node in the tree represents a source file or directory in the code
base and is annotated with four pieces of information:

1. **Platforms**

   The set of platforms that use the file or directory.

2. **SLOC**

   The number of source lines of code (SLOC) in the file or directory.

3. **Coverage (%)**

   The amount of code in the file or directory that is used by all platforms,
   as a percentage of SLOC.

4. **Avg. Coverage (%)**

   The amount of code in the file or directory that is used by each platform,
   on average, as a percentage of SLOC.

The root of the tree represents the entire code base, and so the values in
the annotations match the ``codebasin`` results: two platforms (``A`` and
``B``) use the directory, there are 33 lines in total, 93.94% of those lines
(i.e., 31 lines) are used by at least one platform, and each platform uses
72.73% of those lines (i.e., 24 lines) on average. By walking the tree, we can
break these numbers down across the individual files and directories in the
code base.

Starting with ``main.cpp``, we can see that it is used by both platforms
(``A`` and ``B``), and that 100% of the 13 lines in the file are used by at
least one platform. However, the average coverage is only 92.31%, reflecting
that each platform uses only 12 of those lines.

Turning our attention to ``cpu/foo.cpp`` and ``gpu/foo.cpp``, we can see
that they are each specialized for one platform (``A`` and ``B``,
respectively). The coverage for both files is only 85.71% (i.e., 6 of the 7
lines), which tells us that both files contain some unused code (i.e., 1 line).
The average coverage of 42.86% highlights the extent of the specialization.

.. tip::

   Looking at average coverage is the best way to identify highly specialized
   regions of code. As the number of platforms targeted by a code base
   increases, the average coverage for files used by only a small number of
   platforms will approach zero.

The remaining files all have a coverage of 100.00% and an average coverage
of 100.00%. This is our ideal case: all of the code in the file is used by
at least one platform, and all of the platforms use all of the code.


Filtering Platforms
###################

When working with an application that supports lots of platforms, we may want
to limit the analysis to a subset of the platforms defined in the analysis
file.

Rather than require a separate analysis file for each possible subset, we can
use the :code:`--platform` flag (or :code:`-p` flag) to specify the subset of
interest on the command line:

.. code:: sh

    $ codebasin -p [PLATFORM 1] -p [PLATFORM 2] analysis.toml

For example, we can limit the analysis of our sample code base to the cpu
platform as follows:

.. code:: sh

    $ codebasin -p cpu analysis.toml

or

.. code:: sh

    $ cbi-tree -p cpu analysis.toml
