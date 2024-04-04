# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import config, finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestExclude(unittest.TestCase):
    """
    Simple test of ability to exclude files using patterns.
    """

    def setUp(self):
        self.rootdir = "./tests/exclude/"
        logging.getLogger("codebasin").disabled = True

    def _get_setmap(self, excludes):
        codebase = {
            "files": [],
            "platforms": ["test"],
            "exclude_files": set(),
            "exclude_patterns": excludes,
            "rootdir": os.path.realpath(self.rootdir),
        }
        dbpath = os.path.realpath(os.path.join(self.rootdir, "commands.json"))
        configuration = {"test": config.load_database(dbpath, self.rootdir)}
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        return setmap

    def test_exclude_nothing(self):
        """exclude/nothing"""
        excludes = []
        setmap = self._get_setmap(excludes)
        expected_setmap = {frozenset(["test"]): 4}
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")

    def test_exclude_extension(self):
        """exclude/extension"""
        excludes = ["*.f90"]
        setmap = self._get_setmap(excludes)
        expected_setmap = {frozenset(["test"]): 3}
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")

    def test_exclude_name(self):
        """exclude/name"""
        excludes = ["src/excluded_name.cpp"]
        setmap = self._get_setmap(excludes)
        expected_setmap = {frozenset(["test"]): 3}
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")

    def test_excluded_directory(self):
        excludes = ["thirdparty/"]
        setmap = self._get_setmap(excludes)
        expected_setmap = {frozenset(["test"]): 3}
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")

    def test_excludes(self):
        excludes = ["*.f90", "src/excluded_name.cpp", "thirdparty/"]
        setmap = self._get_setmap(excludes)
        expected_setmap = {frozenset(["test"]): 1}
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")


if __name__ == "__main__":
    unittest.main()
