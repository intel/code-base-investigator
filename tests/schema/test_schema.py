# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import tempfile
import unittest

import codebasin.config as config
import codebasin.util as util


def _test_toml_string(contents: str):
    f = tempfile.NamedTemporaryFile(suffix=".toml")
    f.write(contents.encode())
    f.seek(0)
    _ = util._load_toml(f, "cbiconfig")
    f.close()


class TestSchema(unittest.TestCase):
    """
    Test schema validation of input files.
    """

    def setUp(self):
        logging.disable()

    def test_compilation_database(self):
        """schema/compilation_database"""

        path = "./tests/schema/compile_commands.json"
        _ = config.load_database(path, "")

        with self.assertRaises(ValueError):
            path = "./tests/schema/invalid_compile_commands.json"
            _ = config.load_database(path, "")

    def test_cbiconfig_file(self):
        """schema/cbiconfig_file"""

        path = "./tests/schema/cbiconfig.toml"
        with open(path, "rb") as f:
            toml = util._load_toml(f, "cbiconfig")
            expected = {
                "compiler": {
                    "test_one": {"options": ["TEST_ONE"]},
                    "test_two": {"options": ["TEST_TWO"]},
                },
            }
            self.assertEqual(toml, expected)

        path = "./tests/schema/invalid_cbiconfig.toml"
        with open(path, "rb") as f:
            with self.assertRaises(ValueError):
                toml = util._load_toml(f, "cbiconfig")

    def test_cbiconfig_compilers(self):
        """Check validation of compiler customization"""

        # Compilers can be aliases of other compilers.
        _test_toml_string(
            """
            [compiler.test]
            alias_of = "icc"
        """,
        )

        # Compilers can have options.
        _test_toml_string(
            """
            [compiler.test]
            options = ["-D", "ASDF"]
        """,
        )

        # A compiler alias cannot have options.
        with self.assertRaises(ValueError):
            _test_toml_string(
                """
                [compiler.test]
                alias_of = "icc"
                options = ["-D", "ASDF"]
            """,
            )

        # A compiler cannot define any other keys.
        with self.assertRaises(ValueError):
            _test_toml_string(
                """
                [compiler.test]
                additional = "True"
            """,
            )

        # A compiler can define multiple parser options.
        _test_toml_string(
            """
            [[compiler.test.parser]]
            action = "store_const"
            dest = "defines"
            const = "ASDF"

            [[compiler.test.parser]]
            action = "store"
            dest = "defines"
            default = "one-value"

            [[compiler.test.parser]]
            action = "append"
            dest = "defines"
            default = ["multiple", "values"]

            [[compiler.test.parser]]
            action = "store_split"
            dest = "passes"
            sep = ","
            format = "$value"

            [[compiler.test.parser]]
            action = "extend_match"
            dest = "passes"
            pattern = "*"
            format = "$value"
        """,
        )

        # A compiler cannot define any other parser keys.
        with self.assertRaises(ValueError):
            _test_toml_string(
                """
                [[compiler.test.parser]]
                additional = "True"
            """,
            )

        # A compiler can define multiple modes.
        _test_toml_string(
            """
            [[compiler.test.modes]]
            name = "language"
            defines = ["LANGUAGE"]
            include_paths = ["/language/"]
            include_files = ["language.inc"]

            [[compiler.test.modes]]
            name = "another-language"
            defines = ["ANOTHER_LANGUAGE"]
            include_paths = ["/another-language/"]
            include_files = ["another_language.inc"]
        """,
        )

        # A compiler cannot define any other mode keys.
        with self.assertRaises(ValueError):
            _test_toml_string(
                """
                [[compiler.test.modes]]
                additional = "True"
            """,
            )

        # A compiler can define multiple passes.
        _test_toml_string(
            """
            [[compiler.test.passes]]
            name = "host"
            defines = ["HOST"]
            include_paths = ["/host/"]
            include_files = ["host.inc"]

            [[compiler.test.modes]]
            name = "device"
            defines = ["DEVICE"]
            include_paths = ["/device/"]
            include_files = ["device.inc"]
        """,
        )

        # A compiler cannot define any other pass keys.
        with self.assertRaises(ValueError):
            _test_toml_string(
                """
                [[compiler.test.passes]]
                additional = "True"
            """,
            )

    def test_analysis_file(self):
        """schema/analysis_file"""

        path = "./tests/schema/analysis.toml"
        with open(path, "rb") as f:
            toml = util._load_toml(f, "analysis")
            expected = {
                "codebase": {
                    "exclude": ["*.F90", "*.cu"],
                },
                "platform": {
                    "one": {
                        "commands": "one.json",
                    },
                    "two": {
                        "commands": "two.json",
                    },
                },
            }
            self.assertEqual(toml, expected)

        path = "./tests/schema/invalid_analysis.toml"
        with open(path, "rb") as f:
            with self.assertRaises(ValueError):
                toml = util._load_toml(f, "analysis")


if __name__ == "__main__":
    unittest.main()
