# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestCommentedDirective(unittest.TestCase):
    """
    Simple test of ability to recognize #commented_directive directives
    within files.
    """

    def setUp(self):
        self.rootdir = "./tests/commented_directive/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(["CPU", "GPU"]): 5}

    def count_children_nodes(self, node):
        my_count = 0
        for child in node.children:
            my_count += 1 + self.count_children_nodes(child)

        return my_count

    def test_yaml(self):
        """commented_directive/commented_directive.yaml"""
        codebase = {
            "files": [
                os.path.realpath(os.path.join(self.rootdir, "main.cpp")),
            ],
            "platforms": ["CPU", "GPU"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }
        configuration = {
            "CPU": [
                {
                    "file": codebase["files"][0],
                    "defines": ["CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": codebase["files"][0],
                    "defines": ["GPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)

        node_count = 1
        for fn in state.get_filenames():
            node_count += self.count_children_nodes(state.get_tree(fn).root)

        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )
        self.assertEqual(
            node_count,
            6,
            f"Incorrect number of nodes in tree: {node_count}",
        )


if __name__ == "__main__":
    unittest.main()
