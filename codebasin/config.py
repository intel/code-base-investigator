# Copyright (C) 2019 Intel Corporation
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
import sys

import yaml
from . import util

log = logging.getLogger("codebasin")


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


def load_database(dbpath, rootdir):
    """
    Load a compilation database.
    Return a list of compilation commands, where each command is
    represented as a compilation database entry.
    """
    with util.safe_open_read_nofollow(dbpath, 'r') as fi:
        db = yaml.safe_load(fi)

    configuration = []
    for e in db:
        # Database may not have tokenized arguments
        if "command" in e:
            args = e["command"].split()
        elif "arguments" in e:
            args = e["arguments"]

        # Extract defines, include paths and include files
        # from command-line arguments
        defines = extract_defines(args)
        include_paths = extract_include_paths(args)
        include_files = extract_include_files(args)

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
            configuration += [{"file": path,
                               "defines": defines,
                               "include_paths": include_paths,
                               "include_files": include_files}]
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
