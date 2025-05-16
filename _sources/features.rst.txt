Key Features
============

Identifying Specialization
##########################

CBI is currently limited to identifying two forms of specialization:

1) Different source files are compiled for different platforms;
2) Lines of code within source files are guarded by C preprocessor macros.

Although limited, this functionality is sufficient to support analysis of many
HPC codes, and CBI has been tested on C, C++, CUDA and some Fortran code bases.


Computing Specialization Metrics
################################

CBI computes code divergence and platform coverage by building a
*specialization tree*, like the one shown below:

.. image:: specialization-tree.png
   :alt: An example of a specialization tree.

CBI can then walk and evaluate this tree for different platform definitions, to
produce a report providing a breakdown of how many lines of code are shared
between different platform sets.

.. code:: text

    ---------------------------------------------
                          Platform Set LOC % LOC
    ---------------------------------------------
                                    {}   2  4.88
                               {GPU 1}   1  2.44
                               {GPU 2}   1  2.44
                               {CPU 2}   1  2.44
                               {CPU 1}   1  2.44
                                {FPGA}  14 34.15
                        {GPU 2, GPU 1}   6 14.63
                        {CPU 1, CPU 2}   6 14.63
    {FPGA, CPU 1, GPU 2, GPU 1, CPU 2}   9 21.95
    ---------------------------------------------
    Code Divergence: 0.55
    Coverage (%): 95.12
    Avg. Coverage (%): 42.44
    Total SLOC: 41

For more information about these metrics, see :doc:`here <specialization>`.


Hierarchical Clustering
#######################

Since code divergence is constructed from pair-wise distances, CBI can also
produce a pair-wise distance matrix, showing the ratio of platform-specific
code to code used by both platforms.

.. code:: text

    Distance Matrix
    -----------------------------------
          FPGA CPU 1 GPU 2 GPU 1 CPU 2
    -----------------------------------
     FPGA 0.00  0.70  0.70  0.70  0.70
    CPU 1 0.70  0.00  0.61  0.61  0.12
    GPU 2 0.70  0.61  0.00  0.12  0.61
    GPU 1 0.70  0.61  0.12  0.00  0.61
    CPU 2 0.70  0.12  0.61  0.61  0.00
    -----------------------------------

These distances can also be used to produce a dendrogram, showing the result of
hierarchical clustering by platform similarity.

.. image:: example-dendrogram.png
   :alt: A dendrogram representing the distance between platforms.


Visualizing Platform Coverage
#############################

To assist developers in identifying exactly which parts of their code are
specialized and for which platforms, CBI can produce an annotated tree showing
the amount of specialization within each file.

.. code:: text

    Legend:
    A: cpu
    B: gpu

    Columns:
    [Platforms | SLOC | Coverage (%) | Avg. Coverage (%)]

    [AB | 1.0k |   2.59 |   1.83] o /path/to/sample-code-base/src/
    [-- | 1.0k |   0.00 |   0.00] |-- unused.cpp
    [AB |   13 | 100.00 |  92.31] |-- main.cpp
    [A- |    7 | 100.00 |  50.00] |-o cpu/
    [A- |    7 | 100.00 |  50.00] | \-- foo.cpp
    [-B |    7 | 100.00 |  50.00] \-o gpu/
    [-B |    7 | 100.00 |  50.00]   \-- foo.cpp
