# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions to build up a configuration dictionary,
defining a specific code base configuration.
"""

import argparse
import collections
import logging
import os
import re
import string

from codebasin import CompilationDatabase, util

log = logging.getLogger(__name__)


def extract_defines(argv):
    """
    Extract definitions from command-line arguments.
    Recognizes two argument "-D MACRO" and one argument "-DMACRO".
    """
    defines = []
    prefix = ""
    for a in argv:
        if a == "-D":
            prefix = "-D"
        elif prefix:
            defines += [a]
            prefix = ""
        elif a[0:2] == "-D":
            defines += [a[2:]]
            prefix = ""
    return defines


def extract_include_paths(argv):
    """
    Extract include paths from command-line arguments.
    Recognizes two argument "-I path" and one argument "-Ipath".
    """
    prefixes = ["-I", "-isystem"]

    include_paths = []
    prefix = ""
    for a in argv:
        if a in prefixes:
            prefix = a
        elif prefix in prefixes:
            include_paths += [a]
            prefix = ""
        elif a[0:2] == "-I":
            include_paths += [a[2:]]
    return include_paths


def extract_include_files(argv):
    """
    Extract include files from command-line arguments.
    Recognizes two argument "-include file".
    """
    includes = []
    prefix = ""
    for a in argv:
        if a == "-include":
            prefix = "-include"
        elif prefix:
            includes += [a]
            prefix = ""
    return includes


_importcfg = None


def load_importcfg():
    """
    Load the import configuration file, if it exists.
    """
    global _importcfg
    _importcfg = collections.defaultdict(list)
    path = ".cbi/config"
    if os.path.exists(path):
        log.info(f"Found configuration file at {path}")
        with open(path, "rb") as f:
            try:
                _importcfg_toml = util._load_toml(f, "cbiconfig")
            except ValueError as e:
                log.error(str(e))
                return
        for name, compiler in _importcfg_toml["compiler"].items():
            _importcfg[name] = compiler["options"]


class _StoreSplitAction(argparse.Action):
    """
    A custom argparse.Action that splits the value based on a user-provided
    separator, then stores the resulting list.
    """

    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        self.sep = kwargs.pop("sep", None)
        self.format = kwargs.pop("format", None)
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string):
        if not isinstance(values, str):
            raise TypeError("store_split expects string values")
        split_values = values.split(self.sep)
        if self.format:
            template = string.Template(self.format)
            split_values = [template.substitute(value=v) for v in split_values]
        if self.dest == "passes":
            passes = getattr(namespace, self.dest)
            passes[option_string] = split_values
        else:
            setattr(namespace, self.dest, split_values)


class Compiler:
    """
    Represents the behavior of a specific compiler, including:
    - The number of passes it performs.
    - Implicitly defined macros, which may be flag-dependent.
    """

    def __init__(self, args):
        self.name = os.path.basename(args[0])
        self.args = args
        self.passes = {"default"}

        # Check for any user-defined compiler behavior.
        # Currently, users can only override default defines.
        if _importcfg is None:
            load_importcfg()
        self.defines = extract_defines(_importcfg[self.name])

    def get_passes(self):
        return self.passes.copy()

    def get_defines(self, pass_):
        return self.defines.copy()

    def get_include_paths(self, pass_):
        return []

    def get_include_files(self, pass_):
        return []

    def has_implicit_behavior(self, pass_):
        return (
            self.get_defines(pass_)
            or self.get_include_paths(pass_)
            or self.get_include_files(pass_)
        )

    def get_configuration(self, pass_):
        defines = self.get_defines(pass_)
        include_paths = self.get_include_paths(pass_)
        include_files = self.get_include_files(pass_)
        return {
            "defines": defines,
            "include_paths": include_paths,
            "include_files": include_files,
        }


class ClangCompiler(Compiler):
    """
    Represents the behavior of Clang-based compilers.
    """

    device_passes = [
        "spir64",
        "x86_64",
        "spir64_x86_64",
        "spir64_gen",
        "spir64_fpga",
    ]

    def __init__(self, args):
        super().__init__(args)

        self.sycl = False
        self.omp = False
        sycl_targets = []

        for arg in args:
            if arg == "-fsycl":
                self.sycl = True
                continue

            m = re.search("-fsycl-targets=", arg)
            if m:
                sycl_targets = arg.split("=")[1].split(",")
                self.passes |= set(sycl_targets)
                continue

            if arg in ["-fopenmp", "-fiopenmp", "-qopenmp"]:
                self.omp = True
                continue

            if arg in ["-fsycl-is-device"]:
                self.defines.append("__SYCL_DEVICE_ONLY__")
                continue

        if self.sycl and sycl_targets == []:
            self.passes |= {"spir64"}

    def get_defines(self, pass_):
        defines = super().get_defines(pass_)

        if pass_ in ClangCompiler.device_passes:
            defines.append("__SYCL_DEVICE_ONLY__")

        if "spir64" in pass_ or pass_ == "x86_64":
            defines.append("__SPIR__")
            defines.append("__SPIRV__")

        if pass_ == "default" and self.omp:
            defines.append("_OPENMP")

        return defines


class GnuCompiler(Compiler):
    """
    Represents the behavior of GNU-based compilers.
    """

    def __init__(self, args):
        super().__init__(args)

        for arg in args:
            if arg in ["-fopenmp"]:
                self.defines.append("_OPENMP")
                break


class HipCompiler(Compiler):
    """
    Represents the behavior of the HIP compiler.
    """

    def __init__(self, args):
        super().__init__(args)


class IntelCompiler(ClangCompiler):
    """
    Represents the behavior of Intel compilers.
    """

    def __init__(self, args):
        super().__init__(args)


class NvccCompiler(Compiler):
    """
    Represents the behavior of the NVCC compiler.
    """

    def __init__(self, args):
        super().__init__(args)
        self.omp = False

        for arg in args:
            archs = re.findall("sm_(\\d+)", arg)
            archs += re.findall("compute_(\\d+)", arg)
            self.passes |= set(archs)

            if arg in ["-fopenmp", "-fiopenmp", "-qopenmp"]:
                self.omp = True
                continue

    def get_defines(self, pass_):
        defines = super().get_defines(pass_)

        defines.append("__NVCC__")
        defines.append("__CUDACC__")

        if pass_ != "default":
            arch = int(pass_) * 10
            defines.append(f"__CUDA_ARCH__={arch}")

        if pass_ == "default" and self.omp:
            defines.append("_OPENMP")

        return defines


_seen_compiler = collections.defaultdict(lambda: False)


def recognize_compiler(argv):
    """
    Attempt to recognize the compiler, given an argument list.
    Return a Compiler object.
    """
    compiler = None
    compiler_name = os.path.basename(argv[0])
    if compiler_name in ["clang", "clang++"]:
        compiler = ClangCompiler(argv)
    elif compiler_name in ["gcc", "g++"]:
        compiler = GnuCompiler(argv)
    elif compiler_name in ["hipcc"]:
        compiler = HipCompiler(argv)
    elif compiler_name in ["icx", "icpx", "ifx"]:
        compiler = IntelCompiler(argv)
    elif compiler_name == "nvcc":
        compiler = NvccCompiler(argv)
    else:
        compiler = Compiler(argv)

    if not _seen_compiler[compiler_name]:
        if compiler:
            log.info(f"Recognized compiler: {compiler.name}.")
        else:
            log.warning(
                f"Unrecognized compiler: {compiler_name}. "
                + "Some implicit behavior may be missed.",
            )
        _seen_compiler[compiler_name] = True
    return compiler


def load_database(dbpath, rootdir):
    """
    Load a compilation database.
    Return a list of compilation commands, where each command is
    represented as a compilation database entry.
    """
    db = CompilationDatabase.from_file(dbpath)

    configuration = []
    for command in db:
        if not command.is_supported():
            continue
        argv = command.arguments

        # Extract defines, include paths and include files
        # from command-line arguments
        defines = extract_defines(argv)
        include_paths = extract_include_paths(argv)
        include_files = extract_include_files(argv)

        # Certain tools may have additional, implicit, behaviors
        # (e.g., additional defines, multiple passes for multiple targets)
        compiler = recognize_compiler(argv)

        # Include paths may be specified relative to root
        include_paths = [
            os.path.abspath(os.path.join(rootdir, f)) for f in include_paths
        ]

        # Files may be specified:
        # - relative to root
        # - relative to a directory
        # - as an absolute path
        filedir = rootdir
        if command.directory is not None:
            if os.path.isabs(command.directory):
                filedir = command.directory
            else:
                filedir = os.path.abspath(
                    rootdir,
                    os.path.join(command.directory),
                )

        if os.path.isabs(command.filename):
            path = os.path.abspath(command.filename)
        else:
            path = os.path.abspath(os.path.join(filedir, command.filename))

        # Compilation database may contain files that don't
        # exist without running make
        if os.path.exists(path):
            for pass_ in compiler.get_passes():
                entry = {
                    "file": path,
                    "defines": defines.copy(),
                    "include_paths": include_paths.copy(),
                    "include_files": include_files.copy(),
                }
                if compiler.has_implicit_behavior(pass_):
                    extra_flags = []
                    compiler_config = compiler.get_configuration(pass_)

                    extra_defines = compiler_config["defines"]
                    entry["defines"] += extra_defines
                    extra_flags += [f"-D {x}" for x in extra_defines]

                    extra_include_paths = compiler_config["include_paths"]
                    entry["include_paths"] += extra_include_paths
                    extra_flags += [f"-I {x}" for x in extra_include_paths]

                    extra_include_files = compiler_config["include_files"]
                    entry["include_files"] += extra_include_files
                    extra_flags += [
                        f"-include {x}" for x in extra_include_files
                    ]

                    extra_flag_string = " ".join(extra_flags)
                    log.info(
                        f"Extra flags for {path} in pass '{pass_}': "
                        + f"{extra_flag_string}",
                    )
                configuration += [entry]
        else:
            log.warning("Couldn't find file %s -- ignoring it.", path)

    if len(configuration) == 0:
        log.warning(
            f"No files found in compilation database at '{dbpath}'.\n"
            + "Ensure that 'directory' and 'file' are in the root directory.",
        )

    return configuration
