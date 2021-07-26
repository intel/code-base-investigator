# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions for generating command-line reports.
"""

import itertools as it
import logging
import json

from . import util

log = logging.getLogger("codebasin")


def annotated_dump(output_file, state):
    outlist = []
    for fname in state.get_filenames():
        source_tree = state.get_tree(fname)
        node_associations = state.get_map(fname)
        outlist.append(source_tree.root.to_json(node_associations))

    with open(output_file, 'w') as fp:
        fp.write(json.dumps(outlist, indent=2))


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
    for (c, h) in enumerate(headers):
        widths[c] = max(widths[c], len(h))
    for r in rows:
        for (c, data) in enumerate(r):
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
    for (pset, count) in setmap.items():
        if (p1 in pset) or (p2 in pset):
            total += count
    d = 0
    for (pset, count) in setmap.items():
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
    for (p1, p2) in it.combinations(platforms, 2):
        d += distance(setmap, p1, p2)
        npairs += 1

    if npairs == 0:
        return 0
    return d / float(npairs)


def summary(setmap):
    """
    Produce a summary report for the platform set
    """
    lines = []

    total = sum(setmap.values())
    data = []
    total_count = 0
    for pset in sorted(setmap.keys(), key=len):
        name = "{%s}" % (", ".join(pset))
        count = "%d" % (setmap[pset])
        percent = "%.2f" % ((float(setmap[pset]) / float(total)) * 100)
        data += [[name, count, percent]]
        total_count += setmap[pset]
    lines += [table(["Platform Set", "LOC", "% LOC"], data)]

    lines += ["Code Divergence: %.2f" % (divergence(setmap))]
    lines += ["Unused Code (%%): %.2f" % ((setmap[frozenset()] / total_count) * 100.0)]
    lines += ["Total SLOC: %d" % (total_count)]

    return "\n".join(lines)


def clustering(output_name, setmap):
    """
    Produce a clustering report for the platform set
    """
    # Sort the platform list to ensure that the ordering of platforms in the
    # distance matrix and dendrogram do not change from run to run
    platforms = sorted(extract_platforms(setmap))

    if len(platforms) == 1:
        log.error("Error: clustering is not supported for a single platform.")
        return None

    if not util.ensure_png(output_name):
        log.error("Error: clustering output file name is not a png; skipping creation.")
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
    matrix = [[distance(setmap, p1, p2) for p2 in platforms] for p1 in platforms]

    # Print distance matrix as a table
    lines = []
    lines += ["", "Distance Matrix"]
    labelled_matrix = [[name] + [("%.2f" % column) for column in matrix[row]]
                       for (row, name) in enumerate(platforms)]
    lines += [table([""] + platforms, labelled_matrix)]

    # Hierarchical clustering using average inter-cluster distance
    clusters = hierarchy.linkage(squareform(matrix), method='average')

    # Plot dendrogram of hierarchical clustering
    fig, ax = plt.subplots()
    hierarchy.dendrogram(clusters, labels=platforms, orientation="right")
    ax.set_xlim(xmin=0, xmax=1)
    ax.axvline(x=divergence(setmap), linestyle='--', label="Average")
    plt.text(divergence(setmap), ax.get_ylim()[1], "Average", ha="center", va="bottom")
    plt.xlabel("Code Divergence")
    with util.safe_open_write_binary(output_name) as fp:
        fig.savefig(fp)

    return "\n".join(lines)
