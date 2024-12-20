# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains utility functions for common operations, including:
- Checking file extensions
- Opening files for writing
- Checking paths
"""

import json
import logging
import os
import pkgutil
import tomllib
import typing
from collections.abc import Iterable
from pathlib import Path

import jsonschema

log = logging.getLogger(__name__)


def ensure_ext(path: os.PathLike[str], extensions: Iterable[str]):
    """
    Ensure that a path has one of the specified extensions.

    Parameters
    ----------
    path: os.PathLike[str]
        The path to test.

    extensions: Iterable[str]
        The valid extensions to test against.

    Returns
    -------
    bool
        True if `path` is a file with one of the specified extensions.

    Raises
    ------
    TypeError
        If `path` is not a string or PathLike.
        If `extensions` is not a string or an Iterable of strings.

    ValueError
        If `path` does not have one of the specified extensions.
    """
    path = Path(path)
    if isinstance(extensions, str):
        extensions = [extensions]
    if not all(isinstance(ext, str) for ext in extensions):
        raise TypeError("'extensions' must be 'str' or 'Iterable[str]'")

    extension = "".join(path.suffixes)
    if extension not in extensions:
        exts = ", ".join([f"'{ext}'" for ext in extensions])
        raise ValueError(f"{path} does not have a valid extension: f{exts}")


def safe_open_write_binary(fname):
    """Open fname for (binary) writing. Truncate if not a symlink."""
    fpid = os.open(
        fname,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
        0o666,
    )
    return os.fdopen(fpid, "wb")


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


def _validate_json(json_object: object, schema_name: str) -> bool:
    """
    Validate JSON against a schema.

    Parameters
    ----------
    json_object : Object
        The JSON to validate.

    schema_name : {'compiledb', 'coverage', 'cbiconfig', 'analysis'}
        The schema to validate against.

    Returns
    -------
    bool
        True if the JSON is valid.

    Raises
    ------
    ValueError
        If the JSON fails to validate, or the schema name is unrecognized.

    RuntimeError
        If the schema file cannot be located, or the schema is invalid.
    """
    schema_paths = {
        "analysis": "schema/analysis.schema",
        "compiledb": "schema/compilation-database.schema",
        "coverage": "schema/coverage.schema",
        "cbiconfig": "schema/cbiconfig.schema",
    }
    if schema_name not in schema_paths.keys():
        raise ValueError("Unrecognized schema name.")

    schema_path = schema_paths[schema_name]
    schema_string = pkgutil.get_data("codebasin", schema_path)
    if not schema_string:
        msg = f"Could not locate schema file {schema_path}"
        raise RuntimeError(msg)

    schema = json.loads(schema_string)

    try:
        jsonschema.validate(instance=json_object, schema=schema)
    except jsonschema.exceptions.ValidationError as e:
        msg = f"Failed schema validation against {schema_path}: {e.message}"
        raise ValueError(msg)
    except jsonschema.exceptions.SchemaError:
        msg = f"{schema_path} is not a valid schema"
        raise RuntimeError(msg)

    return True


def _validate_toml(toml_object: object, schema_name: str) -> bool:
    """
    Validate TOML against a schema.

    Parameters
    ----------
    yaml_object : Object
        The YAML to validate.

    schema_name : {'cbiconfig'}
        The schema to validate against.

    Returns
    -------
    bool
        True if the TOML is valid.

    Raises
    ------
    ValueError
        If the TOML fails to validate, or the schema name is unrecognized.

    RuntimeError
        If the schema file cannot be located.
    """
    if schema_name != "cbiconfig":
        raise ValueError("Unrecognized schema name.")

    return _validate_json(toml_object, schema_name)


def _load_json(file_object: typing.TextIO, schema_name: str) -> object:
    """
    Load JSON from file and validate it against a schema.

    Parameters
    ----------
    file_object : typing.TextIO
        The file object to load from.

    schema_name : {'compiledb', 'coverage'}
        The schema to validate against.

    Returns
    -------
    Object
        The loaded JSON.

    Raises
    ------
    ValueError
        If the JSON fails to validate, or the schema name is unrecognized.

    RuntimeError
        If the schema file cannot be located.
    """
    json_object = json.load(file_object)
    _validate_json(json_object, schema_name)
    return json_object


def _load_toml(file_object: typing.TextIO, schema_name: str) -> object:
    """
    Load TOML from file and validate it against a schema.

    Parameters
    ----------
    file_object : typing.TextIO
        The file object to load from.

    schema_name : {'cbiconfig', 'analysis'}
        The schema to validate against.

    Returns
    -------
    Object
        The loaded TOML.

    Raises
    ------
    ValueError
        If the TOML fails to validate, or the schema name is unrecognized.

    RuntimeError
        If the schema file cannot be located.
    """
    toml_object = tomllib.load(file_object)
    _validate_json(toml_object, schema_name)
    return toml_object
