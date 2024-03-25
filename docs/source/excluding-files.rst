Excluding Files
===============

By default, CBI will process any file that it encounters in a compilation
database (including :code:`#include` files). The lines of code in these files
will be included in the code divergence calculation unless:

- The file exists outside of the directory where ``codebasin`` is run.
- The file is explicitly excluded from the analysis.


Using the Analysis File
#######################

Files can be explicitly excluded from an analysis by adding an :code:`exclude`
key to the :code:`codebase` section of the TOML file. Each entry in the exclude
list is a pattern to match files against:

.. code-block:: toml

    [codebase]
    exclude = [
        "pattern",
        "pattern"
    ]

.. note::

    Each pattern is a "pathspec", matching the format used by git. For more
    information, see the `git glossary`_.

.. _`git glossary`: https://git-scm.com/docs/gitglossary


For example, we can use this section to instruct CBI to ignore all files in the
``third-party/`` subdirectory, allowing us to focus on our own code:

.. code-block:: toml

    [codebase]
    exclude = [
        "third-party/"
    ]

Using this new analysis file, the output of ``codebasin`` shows fewer lines
shared between the cpu and gpu platforms:


.. code-block:: text
   :emphasize-lines: 7

    -----------------------
    Platform Set LOC % LOC
    -----------------------
              {}   2  7.41
           {cpu}   7 25.93
           {gpu}   7 25.93
      {cpu, gpu}  11 40.74
    -----------------------
    Code Divergence: 0.56
    Unused Code (%): 7.41
    Total SLOC: 27


Using the Command Line
######################

It is also possible to exclude files directly from the command line, using the
:code:`--exclude` flag (or :code:`-x` flag).

The flag expects exclude patterns to be specified the same way as the TOML
file. To ignore all files in the ``third-party/`` subdirectory as we did
before, we can simply run:

.. code:: sh

    $ codebasin -x "third-party/" analysis.toml

.. tip::

    If a file should *always* be excluded, it's better to specify that in the
    analysis file. The command line approach is best suited to evaluate "what
    if" scenarios, like "what if I excluded all files with a specific
    extension?" (e.g., ``-x "*.cu"``).
