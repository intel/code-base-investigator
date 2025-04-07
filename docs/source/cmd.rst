Command Line Interface
======================

.. code-block:: text

    codebasin [-h] [--version] [-v] [-q] [-R <report>] [-x <pattern>] [-p <platform>] [<analysis-file>]

**positional arguments:**

``analysis-file``
    TOML file describing the analysis to be performed,
    including the codebase and platform descriptions.

**options:**

``-h, --help``
    Show help message and exit.

``--version``
    Display version information and exit.

``-v, --verbose``
    Increase verbosity level.

``-q, --quiet``
    Decrease verbosity level.

``--debug``
    Enable debug mode.

``-R <report>``
    Generate a report of the specified type.

    - ``summary``: code divergence information
    - ``clustering``: distance matrix and dendrogram
    - ``duplicates``: detected duplicate files

``-x <pattern>, --exclude <pattern>``
    Exclude files matching this pattern from the code base.
    May be specified multiple times.

``-p <platform>, --platform <platform>``
    Include the specified platform in the analysis.
    May be specified multiple times.
    If not specified, all platforms will be included.

Tree Tool
---------

The tree tool generates a visualization of the code base where each file and
directory is annotated with information about platform usage and coverage.

.. code-block:: text

    cbi-tree [-h] [--version] [-x <pattern>] [-p <platform>] [--prune] [-L <level>] <analysis-file>

**positional arguments:**

``analysis-file``
    TOML file describing the analysis to be performed, including the codebase and platform descriptions.

**options:**

``-h, --help``
    Display help message and exit.

``--version``
    Display version information and exit.

``-x <pattern>, --exclude <pattern>``
    Exclude files matching this pattern from the code base.
    May be specified multiple times.

``-p <platform>, --platform <platform>``
    Include the specified platform in the analysis.
    May be specified multiple times.
    If not specified, all platforms will be included.

``--prune``
    Prune unused files from the tree.

``-L <level>, --levels <level>``
    Print only the specified number of levels.
