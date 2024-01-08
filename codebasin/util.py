# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains utility functions for common operations, including:
- Checking file extensions
- Opening files for writing
- Checking paths
"""

import hashlib
import json
import logging
import os
from collections.abc import Iterable
from os.path import splitext

import jsonschema

_coverage_schema_id = (
    "https://raw.githubusercontent.com/intel/"
    "p3-analysis-library/p3/schema/coverage-0.1.0.schema"
)
_coverage_schema = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": _coverage_schema_id,
    "title": "Coverage",
    "description": "Lines of code used in each file of a code base.",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "file": {"type": "string"},
            "regions": {
                "type": "array",
                "items": {
                    "type": "array",
                    "prefixItems": [
                        {"type": "integer"},
                        {"type": "integer"},
                        {"type": "integer"},
                    ],
                    "items": False,
                },
            },
        },
        "required": ["file", "regions"],
    },
}

log = logging.getLogger("codebasin")


def compute_file_hash(fname):
    """Return sha512 for fname"""
    chunk_size = 4096
    hasher = hashlib.sha512()
    with safe_open_read_nofollow(fname, "rb") as in_file:
        for chunk in iter(lambda: in_file.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def ensure_ext(fname, extensions):
    """Return true if the path passed in has specified extension"""
    if not isinstance(extensions, Iterable):
        extensions = [extensions]

    split = splitext(fname)
    return len(split) == 2 and split[1].lower() in extensions


def ensure_png(fname):
    """Return true if the path passed in specifies a png"""
    return ensure_ext(fname, ".png")


def ensure_source(fname):
    """Return true if the path passed in specifies a source file"""
    extensions = [
        ".s",
        ".asm",
        ".c",
        ".cpp",
        ".cxx",
        ".c++",
        ".cc",
        ".h",
        ".hpp",
        ".hxx",
        ".h++",
        ".hh",
        ".inc",
        ".inl",
        ".tcc",
        ".icc",
        ".ipp",
    ]
    return ensure_ext(fname, extensions)


def ensure_yaml(fname):
    """Return true if the path passed in specifies a YAML file"""
    return ensure_ext(fname, ".yaml")


def ensure_json(fname):
    """Return true if the path passed in specifies a JSON file"""
    return ensure_ext(fname, ".json")


def safe_open_write_binary(fname):
    """Open fname for (binary) writing. Truncate if not a symlink."""
    fpid = os.open(
        fname,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
        0o666,
    )
    return os.fdopen(fpid, "wb")


def safe_open_read_nofollow(fname, *args, **kwargs):
    """Open fname for reading, but don't follow links."""
    fpid = os.open(fname, os.O_RDONLY | os.O_NOFOLLOW)
    return os.fdopen(fpid, *args, **kwargs)


def valid_path(path):
    """Return true if the path passed in is valid"""
    valid = True

    # Check for null byte character(s)
    if "\x00" in path:
        log.critical("Null byte character in file request.")
        valid = False

    # Check for carriage returns or line feed character(s)
    if ("\n" in path) or ("\r" in path):
        log.critical("Carriage return or line feed character in file request.")
        valid = False

    return valid


def validate_coverage_json(json_string: str) -> bool:
    """
    Validate coverage JSON string against schema.

    Parameters
    ----------
    json_string : String
        The JSON string to validate.

    Returns
    -------
    bool
        True if the JSON string is valid.

    Raises
    ------
    ValueError
        If the JSON string fails to validate.

    TypeError
        If the JSON string is not a string.
    """
    if not isinstance(json_string, str):
        raise TypeError("Coverage must be a JSON string.")

    instance = json.loads(json_string)

    try:
        jsonschema.validate(instance=instance, schema=_coverage_schema)
    except Exception:
        msg = "Coverage string failed schema validation"
        raise ValueError(msg)

    return True
