# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains the Platform class used to specify definitions and include
options for a specific platform.
"""

import os


class Platform():
    """
    Represents a platform, and everything associated with a platform.
    Contains a list of definitions, and include paths.
    """

    def __init__(self, name, _root_dir):
        self._definitions = {}
        self._skip_includes = []
        self._include_paths = []
        self._root_dir = _root_dir
        self.name = name

    def add_include_path(self, path):
        """
        Insert a new path into the list of include paths for this
        platform.
        """
        self._include_paths.append(path)

    def undefine(self, identifier):
        """
        Undefine a macro for this platform, if it's defined.
        """
        if identifier in self._definitions:
            del self._definitions[identifier]

    def define(self, identifier, macro):
        """
        Define a new macro for this platform, only if it's not already
        defined.
        """
        if identifier not in self._definitions:
            self._definitions[identifier] = macro

    def add_include_to_skip(self, fn):
        """
        Define a new macro for this platform, only if it's not already
        defined.
        """
        if fn not in self._skip_includes:
            self._skip_includes.append(fn)

    def process_include(self, fn):
        """
        Return a boolean stating if this include file should be
        processed or skipped.
        """
        return fn not in self._skip_includes

    def is_defined(self, identifier):
        """
        Return a boolean stating if the macro named by 'identifier' is
        defined.
        """
        if identifier in self._definitions:
            return "1"
        return "0"

    def get_macro(self, identifier):
        """
        Return either a macro definition (if it's defined), or None.
        """
        if identifier in self._definitions:
            return self._definitions[identifier]
        return None

    def find_include_file(self, filename, is_system_include=False):
        """
        Determine and return the full path to an include file, named
        'filename' using the include paths for this platform.

        System includes do not include the rootdir, while local includes
        do.
        """
        include_file = None

        local_paths = []
        if not is_system_include:
            local_paths += [self._root_dir]

        # Determine the path to the include file, if it exists
        for path in local_paths + self._include_paths:
            test_path = os.path.realpath(os.path.join(path, filename))
            if os.path.exists(test_path):
                include_file = test_path
                break

        return include_file
