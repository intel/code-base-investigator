# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging

import codebasin.config as config

class TestSchema(unittest.TestCase):
    """
    Test schema validation of input files.
    """

    def setUp(self):
        logging.getLogger("codebasin").disabled = True

    def test_compilation_database(self):
        """schema/compilation_database"""

        path = "./tests/schema/compile_commands.json"
        db = config.load_database(path, "")

        with self.assertRaises(ValueError):
            path = "./tests/schema/invalid_compile_commands.json"
            db = config.load_database(path, "")

    def test_configuration_file(self):
        """schema/configuration_file"""

        path = "./tests/schema/config.yaml"
        config.load(path, "./tests/schema/")

        with self.assertRaises(ValueError):
            path = "./tests/schema/invalid_config.yaml"
            config.load(path, "")

if __name__ == '__main__':
    unittest.main()
