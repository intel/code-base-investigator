# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions for generating command-line reports.
"""

import itertools as it
import logging
import warnings
from collections import defaultdict

from codebasin import util

log = logging.getLogger(__name__)


def extract_platforms(setmap):
    """
    Extract a list of unique platforms from a set map
    """
    unique_platforms = set(it.chain.from_iterable(setmap.keys()))
    return list(unique_platforms)


def table(headers, rows):
    """
    Convert table to ASCII string
    """
    # Determine the cell widths
    widths = [0] * len(headers)
    for c, h in enumerate(headers):
        widths[c] = max(widths[c], len(h))
    for r in rows:
        for c, data in enumerate(r):
            widths[c] = max(widths[c], len(data))
    hline = "-" * (sum(widths) + len(headers))

    # Build the table as a list of strings
    lines = []
    lines += [hline]
    line = [h.rjust(widths[c]) for (c, h) in enumerate(headers)]
    lines += [" ".join(line)]
    lines += [hline]
    for r in rows:
        line = [data.rjust(widths[c]) for (c, data) in enumerate(r)]
        lines += [" ".join(line)]
    lines += [hline]

    return "\n".join(lines)


def distance(setmap, p1, p2):
    """
    Compute distance between two platforms
    """
    total = 0
    for pset, count in setmap.items():
        if (p1 in pset) or (p2 in pset):
            total += count
    d = 0
    for pset, count in setmap.items():
        if (p1 in pset) ^ (p2 in pset):
            d += count / float(total)
    return d


def divergence(setmap):
    """
    Compute code divergence as defined by Harrell and Kitson
    i.e. average of pair-wise distances between platform sets
    """
    platforms = extract_platforms(setmap)

    d = 0
    npairs = 0
    for p1, p2 in it.combinations(platforms, 2):
        d += distance(setmap, p1, p2)
        npairs += 1

    if npairs == 0:
        return 0
    return d / float(npairs)


def utilization(setmap: defaultdict[frozenset[str], int]) -> float:
    """
    Compute the average code utilization for all lines in the setmap.
    i.e., (reused SLOC / total SLOC)

    Parameters
    ----------
    setmap: defaultdict[frozenset[str], int]
        The mapping from platform sets to SLOC.

    Returns
    -------
    float
        The average code utilization, in the range [0, NumPlatforms].
    """
    reused_sloc = 0
    total_sloc = 0
    for k, v in setmap.items():
        reused_sloc += len(k) * v
        total_sloc += v
    if total_sloc == 0:
        return float("nan")

    return reused_sloc / total_sloc


def normalized_utilization(
    setmap: defaultdict[frozenset[str], int],
    total_platforms: int | None = None,
) -> float:
    """
    Compute the average code utilization, normalized for a specific number of
    platforms.

    Parameters
    ----------
    setmap: defaultdict[frozenset[str,int]
        The mapping from platform sets to SLOC.

    total_platforms: int | None, default: None
        The total number of platforms to use as the denominator.
        If None, the denominator will be derived from the setmap.

    Returns
    -------
    float
        The average code utilization, in the range [0, 1].

    Raises
    ------
    ValueError
        If `total_platforms` < the number of platforms in `setmap`.
    """
    original_platforms = len(extract_platforms(setmap))
    if total_platforms is None:
        total_platforms = original_platforms
    if total_platforms < original_platforms:
        raise ValueError(
            "Cannot normalize to fewer platforms than the setmap contains.",
        )

    if total_platforms == 0:
        return float("nan")
    else:
        return utilization(setmap) / total_platforms


def summary(setmap):
    """
    Produce a summary report for the platform set
    """
    lines = []

    total = sum(setmap.values())
    data = []
    total_count = 0
    for pset in sorted(setmap.keys(), key=len):
        name = "{" + ", ".join(pset) + "}"
        count = setmap[pset]
        percent = (float(setmap[pset]) / float(total)) * 100
        data += [[name, str(count), f"{percent:.2f}"]]
        total_count += setmap[pset]
    lines += [table(["Platform Set", "LOC", "% LOC"], data)]

    cd = divergence(setmap)
    nu = normalized_utilization(setmap)
    unused = (setmap[frozenset()] / total_count) * 100.0
    lines += [f"Code Divergence: {cd:.2f}"]
    lines += [f"Code Utilization: {nu:.2f}"]
    lines += [f"Unused Code (%): {unused:.2f}"]
    lines += [f"Total SLOC: {total_count}"]

    return "\n".join(lines)


def clustering(output_name, setmap):
    """
    Produce a clustering report for the platform set
    """
    # Sort the platform list to ensure that the ordering of platforms in the
    # distance matrix and dendrogram do not change from run to run
    platforms = sorted(extract_platforms(setmap))

    if len(platforms) == 1:
        log.error("clustering is not supported for a single platform.")
        return None

    if not util.ensure_png(output_name):
        log.error("clustering output file name must end in '.png'.")
        return None

    # Import additional modules required by clustering report
    # Force Agg backend to matplotlib to avoid DISPLAY errors
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    # Remove misleading axes
    for axis in ["left", "right", "top"]:
        matplotlib.rcParams["axes.spines." + axis] = False

    from scipy.cluster import hierarchy
    from scipy.spatial.distance import squareform

    # Compute distance matrix between platforms
    matrix = [
        [distance(setmap, p1, p2) for p2 in platforms] for p1 in platforms
    ]

    # Print distance matrix as a table
    lines = []
    lines += ["", "Distance Matrix"]
    labelled_matrix = [
        [name] + [f"{column:.2f}" for column in matrix[row]]
        for (row, name) in enumerate(platforms)
    ]
    lines += [table([""] + platforms, labelled_matrix)]

    # Hierarchical clustering using average inter-cluster distance
    clusters = hierarchy.linkage(squareform(matrix), method="average")

    # Plot dendrogram of hierarchical clustering
    # Ignore SciPy warning about axis limits, because we override them
    fig, ax = plt.subplots()
    with warnings.catch_warnings(action="ignore"):
        hierarchy.dendrogram(clusters, labels=platforms, orientation="right")
    ax.set_xlim(xmin=0, xmax=1)
    ax.axvline(x=divergence(setmap), linestyle="--", label="Average")
    ax.text(
        divergence(setmap),
        ax.get_ylim()[1],
        "Average",
        ha="center",
        va="bottom",
    )
    ax.set_xlabel("Code Divergence")
    with util.safe_open_write_binary(output_name) as fp:
        fig.savefig(fp)

    return "\n".join(lines)
