# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions for generating command-line reports.
"""

import filecmp
import hashlib
import itertools as it
import logging
import sys
import warnings
from collections import defaultdict
from pathlib import Path
from typing import TextIO

from tabulate import tabulate

from codebasin import CodeBase, util

log = logging.getLogger(__name__)


def extract_platforms(setmap):
    """
    Extract a list of unique platforms from a set map
    """
    unique_platforms = set(it.chain.from_iterable(setmap.keys()))
    return list(unique_platforms)


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
        return float("nan")
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
        If the number of total SLOC is 0, returns NaN.
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

    total_platforms: int, optional
        The total number of platforms to use as the denominator.
        By default, the denominator will be derived from the setmap.

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
        name = "{" + ", ".join(sorted(pset)) + "}"
        count = setmap[pset]
        percent = (float(setmap[pset]) / float(total)) * 100
        data += [[name, str(count), f"{percent:.2f}"]]
        total_count += setmap[pset]

    lines += [
        tabulate(
            data,
            headers=["Platform Set", "LOC", "% LOC"],
            tablefmt="simple_grid",
            floatfmt=".2f",
            stralign="right",
        ),
    ]

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
    util.ensure_ext(output_name, ".png")

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
    lines += [
        tabulate(
            labelled_matrix,
            headers=platforms,
            tablefmt="simple_grid",
            floatfmt=".2f",
        ),
    ]

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


def find_duplicates(codebase: CodeBase) -> list[set[Path]]:
    """
    Search for duplicate files in the code base.

    Returns
    -------
    list[set[Path]]
        A list of all sets of Paths with identical contents.
    """
    # Search for possible matches using a hash, ignoring symlinks.
    possible_matches = defaultdict(set)
    for path in codebase:
        path = Path(path)
        if path.is_symlink():
            continue
        with open(path, "rb") as f:
            digest = hashlib.file_digest(f, "sha512").hexdigest()
        possible_matches[digest].add(path)

    # Confirm equality for files with the same hash.
    confirmed_matches = []
    for digest, paths in possible_matches.items():
        # Skip files with no hash conflicts.
        if len(paths) == 1:
            continue

        # Check for equality amongst all files in the set.
        # Iterate until we have identified all conflicting hashes.
        remaining = paths.copy()
        while len(remaining) > 1:
            first = remaining.pop()
            matches = {first}
            for path in remaining:
                if filecmp.cmp(first, path, shallow=False):
                    matches.add(path)
            remaining.difference_update(matches)
            if len(matches) > 1:
                confirmed_matches.append(matches)

    return confirmed_matches


def duplicates(codebase: CodeBase, stream: TextIO = sys.stdout):
    """
    Produce a report identifying sets of duplicate files.

    Parameters
    ----------
    codebase: CodeBase
        The code base to search for duplicates.

    stream: TextIO, default: sys.stdout
        The stream to write the report to.
    """
    confirmed_matches = find_duplicates(codebase)

    print("Duplicates", file=stream)
    print("----------", file=stream)

    if len(confirmed_matches) == 0:
        print("No duplicates found.", file=stream)
        return

    for i, matches in enumerate(confirmed_matches):
        print(f"Match {i}:", file=stream)
        for path in matches:
            print(f"- {path}")
