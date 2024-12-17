# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions for generating command-line reports.
"""

import itertools as it
import logging
import numbers
import os
import re
import string
import sys
import warnings
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Self, TextIO

from codebasin import CodeBase, util
from codebasin.finder import ParserState
from codebasin.preprocessor import CodeNode

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


def _human_readable(x: int) -> str:
    """
    Parameters
    ----------
    x: int
        An integer.

    Returns
    -------
    str
        A human-readable representation of x.

    Raises
    ------
    TypeError
        If `x` is not an integer.
    """
    if not isinstance(x, numbers.Integral):
        raise TypeError("x must be Integral")

    digits = len(str(x))
    if digits <= 3:
        return str(x)
    elif digits <= 6:
        return f"{x/10**3:.1f}k"
    elif digits <= 9:
        return f"{x/10**6:.1f}M"
    elif digits <= 12:
        return f"{x/10**9:.1f}G"
    return "??????"


def _strip_colors(s: str) -> str:
    """
    Strip ASCII color codes from a string.

    Parameters
    ----------
    s: str
        The string to strip color codes from.

    Returns
    -------
    str
        A copy of s with all color codes removed.

    Raises
    ------
    TypeError
        If `s` is not a string.
    """
    if not isinstance(s, str):
        raise TypeError("s must be a string")

    return re.sub(r"\033\[[0-9]*m", "", s)


class FileTree:
    """
    A FileTree represents all of the files in a directory using a tree
    structure, with hierarchical tracking of the platform set used by
    each file and directory.
    """

    class Node:
        """
        A FileTree.Node represents a single file or directory in a FileTree.
        """

        def __init__(
            self,
            path,
            setmap=None,
            is_root=False,
        ):
            self.path = Path(path)
            if setmap is None:
                setmap = defaultdict(int)
            self.setmap = setmap
            self.children = {}
            self.is_root = is_root

        @property
        def name(self):
            if self.is_root:
                return str(self.path)
            return str(self.path.name)

        @property
        def platforms(self):
            return extract_platforms(self.setmap)

        @property
        def sloc(self):
            count = 0
            for k, v in self.setmap.items():
                if len(k) == 0:
                    continue
                count += v
            return count

        def is_dir(self):
            return self.path.is_dir()

        def is_symlink(self):
            return self.path.is_symlink()

        def _platforms_str(
            self,
            all_platforms: set[str],
            labels: Iterable[str] = string.ascii_uppercase,
        ) -> str:
            """
            Parameters
            ----------
            all_platforms: set[str]
                The set of all platforms.

            labels: Iterable[str], default: string.ascii_uppercase
                The labels to use in place of real platform names.

            Returns
            -------
            str
                A string representing the platforms used by this Node.
            """
            output = ""
            for i, platform in enumerate(sorted(all_platforms)):
                if platform in self.platforms:
                    if self.is_symlink():
                        color = "\033[96m"
                    else:
                        color = "\033[33m"
                    value = labels[i]
                else:
                    color = "\033[2m"
                    value = "-"
                output += f"{color}{value}\033[0m"
            return output

        def _sloc_str(self, max_used: int, max_total: int) -> str:
            """
            Parameters
            ----------
            max_used: int
                The maximum used SLOC, used to determine formatting width.

            max_total: int
                The maximum total SLOC, used to determine formatting width.

            Returns
            -------
            str
                A string representing the SLOC used by this Node, in the form
                "used / total" with human-readable numbers.
            """
            color = ""
            if len(self.platforms) == 0:
                color = "\033[2m"
            elif self.is_symlink():
                color = "\033[96m"

            used_len = len(_human_readable(max_used))
            total_len = len(_human_readable(max_total))

            used = _human_readable(self.sloc)
            total = _human_readable(sum(self.setmap.values()))

            return f"{color}{used:>{used_len}} / {total:>{total_len}}\033[0m"

        def _divergence_str(self) -> str:
            """
            Returns
            -------
            str
                A string representing code divergence in this Node.
            """
            cd = divergence(self.setmap)
            color = ""
            if len(self.platforms) == 0:
                color = "\033[2m"
            elif self.is_symlink():
                color = "\033[96m"
            elif cd <= 0.25:
                color = "\033[32m"
            elif cd >= 0.75 or len(self.platforms) == 1:
                color = "\033[35m"
            return f"{color}{cd:4.2f}\033[0m"

        def _utilization_str(self, total_platforms: int) -> str:
            """
            Parameters
            ----------
            total_platforms: int
                The number of platforms in the whole FileTree.

            Returns
            -------
            str
                A string representing code utilization in this Node.
            """
            nu = normalized_utilization(self.setmap, total_platforms)

            color = ""
            if len(self.platforms) == 0:
                color = "\033[2m"
            elif self.is_symlink():
                color = "\033[96m"
            elif nu > 0.5:
                color = "\033[32m"
            elif nu <= 0.5:
                color = "\033[35m"

            return f"{color}{nu:4.2f}\033[0m"

        def _meta_str(self, root: Self) -> str:
            """
            Parameters
            ----------
            root: FileTree.Node
                The root of the FileTree containing this FileTree.Node.

            Returns
            -------
            str
                A string representing meta-information for this FileTree.Node.
            """
            max_used = root.sloc
            max_total = sum(root.setmap.values())
            info = [
                self._platforms_str(root.platforms),
                self._sloc_str(max_used, max_total),
                self._divergence_str(),
                self._utilization_str(len(root.platforms)),
            ]
            return "[" + " | ".join(info) + "]"

    def __init__(self, rootdir: str | os.PathLike[str]):
        self.root = FileTree.Node(rootdir, is_root=True)

    def insert(
        self,
        filename: str | os.PathLike[str],
        setmap: defaultdict[str, int],
    ):
        """
        Insert a new file into the tree, creating as many nodes as necessary.

        Parameters
        ----------
        filename: str | os.PathLike[str]
            The filename to add to the tree.

        setmap: dict | None
            The setmap information associated with this filename.
        """
        rootpath = self.root.path
        filepath = Path(filename)

        parent = self.root
        for path in list(reversed(filepath.parents)) + [filepath]:
            # Do not create nodes above the chosen root directory.
            if path == rootpath or not path.is_relative_to(rootpath):
                continue

            # Do not propagate information from symlinks.
            if not filepath.is_symlink():
                for ps in setmap.keys():
                    parent.setmap[ps] += setmap[ps]

            # If this name exists, find the node.
            if parent is not None and path.name in parent.children:
                node = parent.children[path.name]

            # Otherwise, create the node.
            else:
                if not path.is_dir():
                    node = FileTree.Node(path, setmap)
                else:
                    node = FileTree.Node(path)
                parent.children[path.name] = node

            parent = node

    def _print(
        self,
        node: Node,
        prefix: str = "",
        connector: str = "",
        fancy: bool = True,
    ):
        """
        Recursive helper function to print all nodes in a FileTree.

        Parameters
        ----------
        node: Node
            The current FileTree.Node to print.

        prefix: str, default: ""
            The current prefix, built up from previous recursive calls.

        connector: str, default: ""
            The character used to connect this Node to the FileTree.

        fancy: bool, default: True
            Whether to use fancy formatting (including colors).
        """
        if fancy:
            dash = "\u2500"
            cont = "\u251C"
            last = "\u2514"
            vert = "\u2502"
        else:
            dash = "-"
            cont = "|"
            last = "\\"
            vert = "|"

        lines = []

        name = ""
        if node.is_dir():
            name += "\033[94m"
        elif node.is_symlink():
            name += "\033[96m"
        elif len(node.platforms) == 0:
            name += "\033[2m"
        name += node.name
        if node.is_dir():
            name += os.sep
        if node.is_symlink():
            name += "\033[0m"
            name += " -> " + str(node.path.resolve())

        name += "\033[0m"

        meta = node._meta_str(self.root)

        # Print this node.
        stub = "" if node == self.root else dash
        stub += "o" if node.is_dir() else dash
        lines += [f"{meta} {prefix}{connector}{stub} {name}"]

        # Prefix children with spaces or vertical line, depending on position.
        if connector == "":
            next_prefix = ""
        elif connector == last:
            next_prefix = prefix + "  "
        else:
            next_prefix = prefix + vert + " "

        for i, name in enumerate(node.children):
            # Use a different connector for the last child in each directory.
            if i == len(node.children) - 1:
                next_connector = last
            else:
                next_connector = cont
            lines += self._print(
                node.children[name],
                next_prefix,
                next_connector,
                fancy,
            )

        return lines

    def write_to(self, stream: TextIO):
        """
        Write the FileTree to the specified stream.

        Parameters
        ----------
        stream: TextIO
            The text stream to write to.
        """
        lines = self._print(self.root, fancy=stream.isatty())
        output = "\n".join(lines)
        if not stream.isatty():
            output = _strip_colors(output)
        print(output, file=stream)


def files(
    codebase: CodeBase,
    state: ParserState | None = None,
    stream: TextIO = sys.stdout,
):
    """
    Produce a file tree representing the code base.

    Parameters
    ----------
    codebase: CodeBase
        The code base to visualize as a tree.

    state: ParserState, default: None
        An optional ParserState used to annotate the tree with platform
        information.

    stream: TextIO, default: sys.stdout
        The stream to write the report to.

    Raises
    ------
    NotImplementedError
        If the number of directories in the code base is not 1.
    """
    if len(codebase.directories) != 1:
        raise NotImplementedError(
            "'files' report currently requires a code base with 1 directory.",
        )

    # Build up a tree from the list of files.
    tree = FileTree(codebase.directories[0])
    for f in codebase:
        setmap = defaultdict(int)
        if state:
            for node, assoc in state.get_map(f).items():
                if isinstance(node, CodeNode):
                    setmap[frozenset(assoc)] += node.num_lines
        tree.insert(f, setmap)

    print("Files", file=stream)
    print("-----", file=stream)

    # Print a legend.
    legend = []
    legend += ["\033[1mLegend\033[0m:"]
    for i, platform in enumerate(sorted(tree.root.platforms)):
        label = string.ascii_uppercase[i]
        legend += [f"\033[33m{label}\033[0m: {platform}"]
    legend += [""]
    legend += ["\033[1mColumns\033[0m:"]
    header = [
        "Platform Set",
        "Used SLOC / Total SLOC",
        "Code Divergence",
        "Code Utilization",
    ]
    legend += ["[" + " | ".join(header) + "]"]
    legend += [""]
    legend = "\n".join(legend)
    if not stream.isatty():
        legend = _strip_colors(legend)
    print(legend, file=stream)

    # Print the tree.
    tree.write_to(stream)
