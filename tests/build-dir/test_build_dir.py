# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import json
import logging
import tempfile
import unittest
from pathlib import Path

from codebasin import config, finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestBuildDirectories(unittest.TestCase):
    """
    Test ability to correctly handle out-of-tree builds.
    """

    def setUp(self):
        self.rootdir = str(Path(__file__).parent)
        logging.getLogger("codebasin").disabled = False

    def test_absolute_paths(self):
        """
        Test database with build "directory" path but source "file" path.
        All "file" fields are absolute paths.
        """

        source = str(Path(__file__).parent.joinpath("foo.cpp"))

        # CBI only understands how to load compilation databases from file.
        # For now, create temporary files every time we test.
        dir1 = str(Path(__file__).parent.joinpath("build1/"))
        build1 = tempfile.NamedTemporaryFile()
        json1 = [
            {
                "command": f"/usr/bin/c++ -o foo.cpp.o -c {source}",
                "directory": f"{dir1}",
                "file": f"{source}",
            },
        ]
        with open(build1.name, "w") as f:
            json.dump(json1, f)

        dir2 = str(Path(__file__).parent.joinpath("build2/"))
        build2 = tempfile.NamedTemporaryFile()
        json2 = [
            {
                "command": f"/usr/bin/c++ -o foo.cpp.o -c {source}",
                "directory": f"{dir2}",
                "file": f"{source}",
            },
        ]
        with open(build2.name, "w") as f:
            json.dump(json2, f)

        codebase = {
            "files": [source],
            "platforms": ["one", "two"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }

        configuration = {}
        for name, path in [("one", build1.name), ("two", build2.name)]:
            db = config.load_database(path, self.rootdir)
            configuration.update({name: db})

        expected_setmap = {frozenset(["one", "two"]): 1}

        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")

    def test_empty_platform(self):
        """
        Check that we warn if all files from a platform are excluded.
        This may be a sign that the compilation database has incorrect paths.
        """

        source = str(Path(__file__).parent.joinpath("foo.cpp"))

        # CBI only understands how to load compilation databases from file.
        # For now, create temporary files every time we test.
        build = str(Path(__file__).parent.joinpath("build/"))
        tmp = tempfile.NamedTemporaryFile()
        obj = [
            {
                "command": f"/usr/bin/c++ -o foo.cpp.o -c {source}",
                "directory": f"{build}",
                "file": "foo.cpp",
            },
        ]
        with open(tmp.name, "w") as f:
            json.dump(obj, f)

        with self.assertLogs("codebasin", level="WARNING") as log:
            config.load_database(tmp.name, self.rootdir)

        found_expected_warning = False
        for msg in log.output:
            if msg.find("No files found in compilation database"):
                found_expected_warning = True
        self.assertTrue(found_expected_warning)


if __name__ == "__main__":
    unittest.main()
