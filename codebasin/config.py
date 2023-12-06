# Copyright (C) 2019-2023 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions to build up a configuration dictionary,
defining a specific code base configuration.
"""

import os
import collections
import glob
import itertools as it
import logging
import re
import shlex
import sys

import yaml
import json
import jsonschema
from . import util

log = logging.getLogger("codebasin")

_compiledb_schema_id = (
    "https://raw.githubusercontent.com/intel/"
    "code-base-investigator/schema/compilation-database.schema"
)
_compiledb_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": _compiledb_schema_id,
    "title": "Compilation Database",
    "description": "Compilation database format used by many projects.",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "directory": {
                "type": "string"
            },
            "arguments": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "file": {
                "type": "string"
            },
            "command": {
                "type": "string"
            },
            "output": {
                "type": "string"
            },
        },
        "anyOf": [
            {
                "required": [
                    "arguments",
                ],
            },
            {
                "required": [
                    "command",
                ]
            }
        ]
    }
}

_config_schema_id = (
    "https://raw.githubusercontent.com/intel/"
    "code-base-investigator/schema/config.schema"
)

_config_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": _config_schema_id,
    "title": "Code Base Investigator Configuration File",
    "description": "Lists codebase files and compilation options",
    "type": "object",
    "properties": {
        "codebase": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "exclude_files": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": [
                "files",
                "platforms"
            ]
        }
    },
    "patternProperties": {
        ".*": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "defines": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "include_paths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "commands": {
                    "type": "string"
                }
            },
            "anyOf": [
                {
                    "required": [
                        "files"
                    ]
                },
                {
                    "required": [
                        "commands"
                    ]
                }
            ]
        }
    },
    "additionalProperties": False,
    "required": [
        "codebase"
    ]
}


def extract_defines(args):
    """
    Extract definitions from command-line arguments.
    Recognizes two argument "-D MACRO" and one argument "-DMACRO".
    """
    defines = []
    prefix = ""
    for a in args:
        if a == "-D":
            prefix = "-D"
        elif prefix:
            defines += [a]
            prefix = ""
        elif a[0:2] == "-D":
            defines += [a[2:]]
            prefix = ""
    return defines


def extract_include_paths(args):
    """
    Extract include paths from command-line arguments.
    Recognizes two argument "-I path" and one argument "-Ipath".
    """
    prefixes = ["-I", "-isystem"]

    include_paths = []
    prefix = ""
    for a in args:
        if a in prefixes:
            prefix = a
        elif prefix in prefixes:
            include_paths += [a]
            prefix = ""
        elif a[0:2] == "-I":
            include_paths += [a[2:]]
    return include_paths


def extract_include_files(args):
    """
    Extract include files from command-line arguments.
    Recognizes two argument "-include file".
    """
    includes = []
    prefix = ""
    for a in args:
        if a == "-include":
            prefix = "-include"
        elif prefix:
            includes += [a]
            prefix = ""
    return includes


def expand_path(pattern):
    """
    Return all valid and existing paths matching a specified pattern.
    """
    if sys.version_info >= (3, 5):
        paths = glob.glob(pattern, recursive=True)
    else:
        if "**" in pattern:
            log.warning("Recursive path expansion with '**' requires Python >= 3.5")
        paths = glob.glob(pattern)
    if paths == []:
        log.warning("Couldn't find files matching '%s' -- ignoring it.", pattern)
    return [os.path.realpath(path) for path in filter(util.valid_path, paths)]


def flatten(nested_list):
    """
    Flatten an arbitrarily nested list.
    Nesting may occur when anchors are used inside a YAML list.
    """
    flattened = []
    for l in nested_list:
        if isinstance(l, list):
            flattened.extend(flatten(l))
        else:
            flattened.append(l)
    return flattened


def load_codebase(config, rootdir):
    """
    Load the code base definition into a Python object.
    Return a dict of files and platform names.
    """
    # Ensure expected values are present, or provide defaults
    cfg_codebase = config["codebase"]
    if not cfg_codebase:
        raise RuntimeError("Empty 'codebase' section found in config file!")
    if "files" not in cfg_codebase or cfg_codebase["files"] == []:
        raise RuntimeError("Empty 'files' section found in codebase definition!")
    if "platforms" not in cfg_codebase or cfg_codebase["platforms"] == []:
        raise RuntimeError("Empty 'platforms' section found in codebase definition!")

    codebase = {"files": list(it.chain(*(expand_path(os.path.join(rootdir, f))
                                         for f in cfg_codebase["files"]))),
                "platforms": cfg_codebase["platforms"]}

    if "exclude_files" in cfg_codebase:
        codebase["exclude_files"] = frozenset(it.chain(*(expand_path(os.path.join(rootdir, f))
                                                         for f in cfg_codebase["exclude_files"])))
    else:
        codebase["exclude_files"] = frozenset([])

    # Ensure that the codebase actually specifies valid files
    if not codebase["files"]:
        raise RuntimeError("Specified codebase contains no valid files -- " +
                           "regular expressions and/or working directory may be incorrect.")

    return codebase


class Compiler(object):
    """
    Represents the behavior of a specific compiler, including:
    - The number of passes it performs.
    - Implicitly defined macros, which may be flag-dependent.
    """

    def __init__(self, args):
        self.name = os.path.basename(args[0])
        self.args = args
        self.passes = set(["default"])

        self.defines = []

    def get_passes(self):
        return self.passes.copy()

    def get_defines(self, pass_):
        return self.defines.copy()

    def get_include_paths(self, pass_):
        return []

    def get_include_files(self, pass_):
        return []

    def has_implicit_behavior(self, pass_):
        return (self.get_defines(pass_) or
                self.get_include_paths(pass_) or
                self.get_include_files(pass_))

    def get_configuration(self, pass_):
        defines = self.get_defines(pass_)
        include_paths = self.get_include_paths(pass_)
        include_files = self.get_include_files(pass_)
        return {"defines": defines,
                "include_paths": include_paths,
                "include_files": include_files}


class ClangCompiler(Compiler):
    """
    Represents the behavior of Clang-based compilers.
    """

    device_passes = [
        "spir64",
        "x86_64",
        "spir64_x86_64",
        "spir64_gen",
        "spir64_fpga"
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
            self.passes |= set(["spir64"])

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
def recognize_compiler(args):
    """
    Attempt to recognize the compiler, given an argument list.
    Return a Compiler object.
    """
    compiler = None
    compiler_name = os.path.basename(args[0])
    if compiler_name in ["clang", "clang++"]:
        compiler = ClangCompiler(args)
    elif compiler_name in ["gcc", "g++"]:
        compiler = GnuCompiler(args)
    elif compiler_name in ["hipcc"]:
        compiler = HipCompiler(args)
    elif compiler_name in ["icx", "icpx", "ifx"]:
        compiler = IntelCompiler(args)
    elif compiler_name == "nvcc":
        compiler = NvccCompiler(args)

    if compiler:
        log.info(f"Recognized compiler: {compiler.name}.")
    else:
        compiler = Compiler(args)
        if not _seen_compiler[compiler_name]:
            log.warning(f"Unrecognized compiler: {compiler_name}. " +
                        "Some implicit behavior may be missed.")
            _seen_compiler[compiler_name] = True
    return compiler


def load_database(dbpath, rootdir):
    """
    Load a compilation database.
    Return a list of compilation commands, where each command is
    represented as a compilation database entry.
    """
    with util.safe_open_read_nofollow(dbpath, 'r') as fi:
        db = json.load(fi)

    # Validate compilation database against schema
    try:
        jsonschema.validate(instance=db, schema=_compiledb_schema)
    except Exception:
        msg = "Compilation database failed schema validation"
        raise ValueError(msg)

    configuration = []
    for e in db:
        # Database may not have tokenized arguments
        if "command" in e:
            args = shlex.split(e["command"])
        elif "arguments" in e:
            args = e["arguments"]

        # Extract defines, include paths and include files
        # from command-line arguments
        defines = extract_defines(args)
        include_paths = extract_include_paths(args)
        include_files = extract_include_files(args)

        # Certain tools may have additional, implicit, behaviors
        # (e.g., additional defines, multiple passes for multiple targets)
        compiler = recognize_compiler(args)

        # Include paths may be specified relative to root
        include_paths = [os.path.realpath(os.path.join(rootdir, f)) for f in include_paths]

        # Files may be specified:
        # - relative to root
        # - relative to a directory
        # - as an absolute path
        filedir = rootdir
        if "directory" in e:
            if os.path.isabs(e["directory"]):
                filedir = e["directory"]
            else:
                filedir = os.path.realpath(rootdir, os.path.join(e["directory"]))

        if os.path.isabs(e["file"]):
            path = os.path.realpath(e["file"])
        else:
            path = os.path.realpath(os.path.join(filedir, e["file"]))

        # Compilation database may contain files that don't
        # exist without running make
        if os.path.exists(path):
            for pass_ in compiler.get_passes():
                entry = {"file": path,
                         "defines": defines,
                         "include_paths": include_paths,
                         "include_files": include_files}
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
                    extra_flags += [f"-include {x}" for x in extra_include_files]

                    extra_flag_string = " ".join(extra_flags)
                    log.info(f"Extra flags for {path} in pass '{pass_}': " +
                             f"{extra_flag_string}")
                configuration += [entry]
        else:
            log.warning("Couldn't find file %s -- ignoring it.", path)

    return configuration


def load_platform(config, rootdir, platform_name):
    """
    Load the platform specified by platform_name into a Python object.
    Return a list of compilation commands, where each command is
    represented as a compilation database entry.
    """
    # Ensure expected values are present, or provide defaults
    cfg_platform = config[platform_name]
    if not cfg_platform:
        raise RuntimeError("Could not find definition for platform " +
                           "'{}' in config file!".format(platform_name))
    if "files" not in cfg_platform and "commands" not in cfg_platform:
        raise RuntimeError("Need 'files' or 'commands' section in " +
                           "definition of platform {}!".format(platform_name))
    if "files" not in cfg_platform:
        if "defines" in cfg_platform or "include_paths" in cfg_platform:
            log.warning("Extra 'defines' or 'include_paths' in definition of platform %s!",
                        platform_name)
    else:
        if "defines" not in cfg_platform:
            cfg_platform["defines"] = []
        if "include_paths" not in cfg_platform:
            cfg_platform["include_paths"] = []

    # Combine manually specified files, defines and includes
    # into configuration entries
    configuration = []
    if "files" in cfg_platform:
        include_paths = [os.path.realpath(os.path.join(rootdir, f))
                         for f in flatten(cfg_platform["include_paths"])]

        # Strip optional -D prefix from defines
        defines = [d[2:] if d.startswith("-D") else d
                   for d in flatten(cfg_platform["defines"])]

        for f in flatten(cfg_platform["files"]):
            for path in expand_path(os.path.join(rootdir, f)):
                configuration += [{"file": path,
                                   "defines": defines,
                                   "include_paths": include_paths,
                                   "include_files": []}]

    # Add configuration entries from a compilation database
    if "commands" in cfg_platform:
        dbpath = os.path.realpath(os.path.join(rootdir, cfg_platform["commands"]))
        configuration += load_database(dbpath, rootdir)

    # Ensure that the platform actually specifies valid files
    if not configuration:
        raise RuntimeError("Platform '{!s}' contains no valid files -- ".format(platform_name) +
                           "regular expressions and/or working directory may be incorrect.")

    return configuration


def load(config_file, rootdir):
    """
    Load the configuration file into Python objects.
    Return a (codebase, platform configuration) tuple of dicts.
    """
    if os.path.isfile(config_file):
        with util.safe_open_read_nofollow(config_file, 'r') as f:
            config = yaml.safe_load(f)
    else:
        raise RuntimeError("Could not open {!s}.".format(config_file))

    # Validate config against a schema
    # We don't use any advanced features of YAML, so can use JSON here
    try:
        jsonschema.validate(instance=config, schema=_config_schema)
    except Exception:
        msg = "Configuration file failed schema validation"
        raise ValueError(msg)

    # Read codebase definition
    if "codebase" in config:
        codebase = load_codebase(config, rootdir)
    else:
        raise RuntimeError("Missing 'codebase' section in config file!")

    log.info("Platforms: %s", ", ".join(codebase["platforms"]))

    # Read each platform definition and populate platform configuration
    configuration = collections.defaultdict(list)
    for platform_name in codebase["platforms"]:
        configuration[platform_name] = load_platform(config, rootdir, platform_name)

    return codebase, configuration
