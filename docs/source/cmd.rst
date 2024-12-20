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

``-R <report>``
    Generate a report of the specified type.

    - ``summary``: output only code divergence information.
    - ``clustering``: output only distance matrix and dendrogram.
    - ``duplicates``: output only detected duplicate files.
    - ``files``: output only information about individual files.
    - ``all``: generate all available reports.

``-x <pattern>, --exclude <pattern>``
    Exclude files matching this pattern from the code base.
    May be specified multiple times.

``-p <platform>, --platform <platform>``
    Include the specified platform in the analysis.
    May be specified multiple times.
    If not specified, all platforms will be included.
