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

In our example, we have two platforms that we're calling "cpu" and "gpu",
and our build directories are called ``build-cpu`` and ``build-gpu``, so
our platform definitions should look like this:

.. code-block:: toml

    [platform.cpu]
    commands = "build-cpu/compile_commands.json"

    [platform.gpu]
    commands = "build-gpu/compile_commands.json"

.. warning::
    Platform names are case sensitive! The names "cpu" and "CPU" would refer to
    two different platforms.


Running ``codebasin``
#####################

Running ``codebasin`` with this analysis file gives the following output:

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
    Unused Code (%): 6.06
    Total SLOC: 33

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
