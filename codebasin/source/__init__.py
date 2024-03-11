# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import os
from enum import Enum, auto


class Language(Enum):
    ASM = auto()
    C = auto()
    CPLUSPLUS = auto()
    FORTRAN_FREE = auto()
    FORTRAN_MIXED = auto()
    UNKNOWN = auto()

    @classmethod
    def from_extension(cls, ext: str) -> "Language":
        if ext in [".s", ".S", ".asm"]:
            return cls.ASM

        if ext in [".c", ".h"]:
            return cls.C

        if ext in [
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
        ]:
            return cls.CPLUSPLUS

        if ext in [".f90", ".F90"]:
            return cls.FORTRAN_FREE

        if ext in [".f", ".ftn", ".fpp", ".F", ".FOR", ".FTN", ".FPP"]:
            return cls.FORTRAN_FIXED

        return cls.UNKNOWN

    @classmethod
    def from_path(cls, path: str) -> "Language":
        ext = os.path.splitext(path)[1]
        return cls.from_extension(ext)
