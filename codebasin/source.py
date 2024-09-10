# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path


def is_source_file(filename: str | os.PathLike) -> bool:
    """
    Parameters
    ----------
    filename: Union[str, os.Pathlike]
        The filename of a potential source file.

    Returns
    -------
    bool
        True if the file ends in a recognized extension and False otherwise.
        Only files that can be parsed correctly have recognized extensions.

    Raises
    ------
    TypeError
        If filename is not a string or Path.
    """
    if not (isinstance(filename, str) or isinstance(filename, Path)):
        raise TypeError("filename must be a string or Path")

    extension = Path(filename).suffix
    supported_extensions = [
        ".f90",
        ".F90",
        ".f",
        ".ftn",
        ".fpp",
        ".F",
        ".FOR",
        ".FTN",
        ".FPP",
        ".c",
        ".h",
        ".c++",
        ".cxx",
        ".cpp",
        ".cc",
        ".hpp",
        ".hxx",
        ".h++",
        ".hh",
        ".inc",
        ".inl",
        ".tcc",
        ".icc",
        ".ipp",
        ".cu",
        ".cuh",
        ".cl",
        ".s",
        ".S",
        ".asm",
    ]
    return extension in supported_extensions
