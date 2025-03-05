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
from dataclasses import asdict, dataclass

from codebasin import CompilationDatabase, util

log = logging.getLogger(__name__)


_importcfg = None


def _parse_compiler_args(argv: list[str]):
    """
    Parameters
    ----------
    argv: list[str]
        A list of arguments passed to a compiler.

    Returns
    -------
    argparse.Namespace
        The result of parsing `argv[1:]`.
        - defines: -D arguments
        - include_paths: -I/-isystem arguments
        - include_files: -include arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-D", dest="defines", action="append", default=[])
    parser.add_argument(
        "-I",
        "-isystem",
        dest="include_paths",
        action="append",
        default=[],
    )
    parser.add_argument(
        "-include",
        dest="include_files",
        action="append",
        default=[],
    )
    args, _ = parser.parse_known_args(argv)
    return args


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

    def __init__(
        self,
        option_strings: list[str],
        dest: str,
        nargs=None,
        **kwargs,
    ):
        self.sep = kwargs.pop("sep", None)
        self.format = kwargs.pop("format", None)
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str,
        option_string: str,
    ):
        if not isinstance(values, str):
            raise TypeError("store_split expects string values")
        split_values = values.split(self.sep)
        if self.format:
            template = string.Template(self.format)
            split_values = [template.substitute(value=v) for v in split_values]
        if self.dest == "passes":
            passes = getattr(namespace, "_passes")
            passes[option_string] = split_values
        else:
            setattr(namespace, self.dest, split_values)


class _ExtendMatchAction(argparse.Action):
    """
    A custom argparse.Action that matches the value against a user-provided
    pattern, then extends the destination list using the result(s).
    """

    def __init__(
        self,
        option_strings: list[str],
        dest: str,
        nargs=None,
        **kwargs,
    ):
        self.pattern = kwargs.pop("pattern", None)
        self.format = kwargs.pop("format", None)
        self.override = kwargs.pop("override", False)
        self.flag_name = option_strings[0]
        super().__init__(option_strings, dest, nargs=nargs, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        value: str,
        option_string: str,
    ):
        if not isinstance(value, str):
            raise TypeError("extend_match expects string value")
        matches = re.findall(self.pattern, value)
        if self.format:
            template = string.Template(self.format)
            matches = [template.substitute(value=v) for v in matches]
        if self.dest == "passes":
            passes = getattr(namespace, "_passes")
            if self.flag_name not in passes:
                passes[self.flag_name] = []
            if self.override:
                passes[self.flag_name] = matches
                self.override = False
            else:
                passes[self.flag_name].extend(matches)
        else:
            if self.override:
                setattr(namespace, self.dest, matches)
            else:
                dest = getattr(namespace, self.dest)
                dest.extend(matches)


@dataclass
class PreprocessorConfiguration:
    """
    Represents the configuration for a specific file, including:
    - Macro definitions
    - Include paths
    - Include files
    - A meaningful pass name
    """

    defines: list[str]
    include_paths: list[str]
    include_files: list[str]
    pass_name: str = "default"


class ArgumentParser:
    """
    Represents the behavior of a specific compiler.
    """

    def __init__(self, path: str):
        self.name = os.path.basename(path)

        # Check for any user-defined compiler behavior.
        # Currently, users can only override default defines.
        if _importcfg is None:
            load_importcfg()

    def parse_args(self, argv: list[str]) -> list[PreprocessorConfiguration]:
        """
        Parameters
        ----------
        argv: list[str]
            The list of arguments passed to the compiler.

        Returns
        -------
        list[PreprocessorConfiguration]
            A list of compiler configurations, each representing
            a separate pass, that describe the compiler's behavior
            after parsing `argv`.
        """
        args = _parse_compiler_args(argv + _importcfg[self.name])
        configuration = PreprocessorConfiguration(
            args.defines,
            args.include_paths,
            args.include_files,
        )
        return [configuration]


class ClangArgumentParser(ArgumentParser):
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

    def parse_args(self, argv: list[str]) -> list[PreprocessorConfiguration]:
        args = _parse_compiler_args(argv + _importcfg[self.name])

        sycl = False
        omp = False
        sycl_targets = []
        passes = {"default"}

        for arg in argv:
            if arg == "-fsycl":
                sycl = True
                continue

            m = re.search("-fsycl-targets=", arg)
            if m:
                sycl_targets = arg.split("=")[1].split(",")
                passes |= set(sycl_targets)
                continue

            if arg in ["-fopenmp", "-fiopenmp", "-qopenmp"]:
                omp = True
                continue

            if arg in ["-fsycl-is-device"]:
                args.defines.append("__SYCL_DEVICE_ONLY__")
                continue

        if sycl and sycl_targets == []:
            passes |= {"spir64"}

        configurations = []
        for pass_ in passes:
            defines = args.defines.copy()
            include_files = args.include_files.copy()
            include_paths = args.include_paths.copy()

            if pass_ in ClangArgumentParser.device_passes:
                defines.append("__SYCL_DEVICE_ONLY__")

            if "spir64" in pass_ or pass_ == "x86_64":
                defines.append("__SPIR__")
                defines.append("__SPIRV__")

            if pass_ == "default" and omp:
                defines.append("_OPENMP")

            configuration = PreprocessorConfiguration(
                defines,
                include_paths,
                include_files,
                pass_name=pass_,
            )

            configurations.append(configuration)

        return configurations


class GnuArgumentParser(ArgumentParser):
    """
    Represents the behavior of GNU-based compilers.
    """

    def parse_args(self, argv: list[str]) -> list[PreprocessorConfiguration]:
        args = _parse_compiler_args(argv + _importcfg[self.name])
        for arg in argv:
            if arg == "-fopenmp":
                args.defines.append("_OPENMP")
        configuration = PreprocessorConfiguration(
            args.defines,
            args.include_paths,
            args.include_files,
        )
        return [configuration]


class NvccArgumentParser(ArgumentParser):
    """
    Represents the behavior of the NVCC compiler.
    """

    def parse_args(self, argv: list[str]) -> list[PreprocessorConfiguration]:
        args = _parse_compiler_args(argv + _importcfg[self.name])

        omp = False
        passes = {"default"}

        for arg in argv:
            archs = re.findall("sm_(\\d+)", arg)
            archs += re.findall("compute_(\\d+)", arg)
            passes |= set(archs)

            if arg in ["-fopenmp", "-fiopenmp", "-qopenmp"]:
                omp = True
                continue

        configurations = []
        for pass_ in passes:
            defines = args.defines.copy()
            include_files = args.include_files.copy()
            include_paths = args.include_paths.copy()

            defines.append("__NVCC__")
            defines.append("__CUDACC__")

            if pass_ != "default":
                # The __CUDA_ARCH__ macro always has three digits.
                # Multiplying the SM version by 10 gives the macro value.
                # e.g., sm_71 corresponds to __CUDA_ARCH__=710.
                arch = int(pass_) * 10
                defines.append(f"__CUDA_ARCH__={arch}")

            if pass_ == "default" and omp:
                defines.append("_OPENMP")

            configuration = PreprocessorConfiguration(
                defines,
                include_paths,
                include_files,
                pass_name=pass_,
            )

            configurations.append(configuration)

        return configurations


_seen_compiler = collections.defaultdict(lambda: False)


def recognize_compiler(path: str) -> ArgumentParser:
    """
    Attempt to recognize the compiler, given a path.
    Return a ArgumentParser object.
    """
    parser = None
    compiler_name = os.path.basename(path)
    if compiler_name in ["clang", "clang++"]:
        parser = ClangArgumentParser(path)
    elif compiler_name in ["gcc", "g++"]:
        parser = GnuArgumentParser(path)
    elif compiler_name in ["icx", "icpx", "ifx"]:
        parser = ClangArgumentParser(path)
    elif compiler_name == "nvcc":
        parser = NvccArgumentParser(path)
    else:
        parser = ArgumentParser(path)

    if not _seen_compiler[compiler_name]:
        if parser:
            log.info(f"Recognized compiler: {compiler_name}.")
        else:
            log.warning(
                f"Unrecognized compiler: {compiler_name}. "
                + "Some implicit behavior may be missed.",
            )
        _seen_compiler[compiler_name] = True
    return parser


def load_database(dbpath, rootdir):
    """
    Load a compilation database.
    Return a list of compilation commands, where each command is
    represented as a compilation database entry.
    """
    db = CompilationDatabase.from_file(dbpath)

    configuration = []
    for command in db:
        # Skip commands that invoke unsupported tools.
        if not command.is_supported():
            continue

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

        # Skip files that don't exist.
        # (e.g., because they're generated by running make)
        if not os.path.exists(path):
            log.warning("Ignoring non-existent file: %s", path)
            continue

        # Parse command-line arguments, emulating compiler-specific behavior.
        compiler_name = os.path.basename(command.arguments[0])
        parser = recognize_compiler(compiler_name)
        preprocessor_configs = parser.parse_args(command.arguments[1:])

        # Create a configuration entry for each compiler pass.
        # Each compiler pass may set different defines, etc.
        for preprocessor_config in preprocessor_configs:
            entry = asdict(preprocessor_config)

            entry["file"] = path

            # Include paths may be specified relative to root
            entry["include_paths"] = [
                os.path.abspath(os.path.join(rootdir, f))
                for f in entry["include_paths"]
            ]

            configuration += [entry]

            # Print variables for debugging purposes.
            if not log.isEnabledFor(logging.DEBUG):
                continue
            pass_name = entry["pass_name"]
            for v in ["defines", "include_paths", "include_files"]:
                if entry[v]:
                    value = " ".join(entry[v])
                    log.debug(f"{v} for {path} in pass '{pass_name}': {value}")

    if len(configuration) == 0:
        log.warning(
            f"No files found in compilation database at '{dbpath}'.\n"
            + "Ensure that 'directory' and 'file' are in the root directory.",
        )

    return configuration
