# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import tempfile
import unittest
from pathlib import Path

from codebasin import config
from codebasin.config import ArgumentParser


class TestCompilers(unittest.TestCase):
    """
    Test that a subset of common compilers and their arguments are recognized
    correctly, and that any implicit behavior(s) are activated.
    """

    def setUp(self):
        logging.disable()
        self.cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_common(self):
        """compilers/common"""
        argv = [
            "c++",
            "-I/path",
            "-I",
            "/path/after/space",
            "-isystem",
            "/system/path",
            "-include",
            "foo.inc",
            "-include",
            "bar.inc",
            "-DMACRO",
            "-DFUNCTION_MACRO=1",
            "-D",
            "MACRO_AFTER_SPACE",
            "test.cpp",
        ]
        parser = ArgumentParser(argv[0])

        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 1)

        self.assertEqual(passes[0].pass_name, "default")

        self.assertCountEqual(
            passes[0].defines,
            ["MACRO", "FUNCTION_MACRO=1", "MACRO_AFTER_SPACE"],
        )
        self.assertCountEqual(
            passes[0].include_paths,
            ["/path", "/path/after/space", "/system/path"],
        )
        self.assertCountEqual(passes[0].include_files, ["foo.inc", "bar.inc"])

    def test_gnu(self):
        """compilers/gnu"""
        argv = ["g++", "-fopenmp", "test.cpp"]

        parser = ArgumentParser(argv[0])

        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 1)

        self.assertEqual(passes[0].pass_name, "default")

        defines = passes[0].defines
        self.assertCountEqual(defines, ["_OPENMP"])

    def test_clang(self):
        """compilers/clang"""
        argv = ["clang", "-fsycl-is-device", "test.cpp"]

        parser = ArgumentParser(argv[0])

        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 1)

        self.assertEqual(passes[0].pass_name, "default")

        defines = passes[0].defines
        self.assertCountEqual(defines, ["__SYCL_DEVICE_ONLY__"])

    def test_intel_sycl(self):
        """compilers/intel_sycl"""
        argv = ["icpx", "-fsycl", "test.cpp"]

        parser = ArgumentParser(argv[0])

        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 2)

        pass_names = {p.pass_name for p in passes}
        self.assertCountEqual(pass_names, {"default", "sycl-spir64"})

        for p in passes:
            if p.pass_name == "default":
                expected = ["SYCL_LANGUAGE_VERSION"]
            else:
                expected = [
                    "SYCL_LANGUAGE_VERSION",
                    "__SYCL_DEVICE_ONLY__",
                    "__SPIR__",
                    "__SPIRV__",
                ]
            self.assertCountEqual(p.defines, expected)

    def test_intel_targets(self):
        """compilers/intel_targets"""
        argv = [
            "icpx",
            "-fsycl",
            "-fsycl-targets=spir64,spir64_x86_64",
            "-fopenmp",
            "test.cpp",
        ]

        parser = ArgumentParser(argv[0])

        passes = parser.parse_args(argv[1:])

        pass_names = {p.pass_name for p in passes}
        self.assertCountEqual(
            pass_names,
            {"default", "sycl-spir64", "sycl-spir64_x86_64"},
        )

        for p in passes:
            if p.pass_name == "default":
                expected = ["SYCL_LANGUAGE_VERSION", "_OPENMP"]
            elif (
                p.pass_name == "sycl-spir64"
                or p.pass_name == "sycl-spir64_x86_64"
            ):
                expected = [
                    "SYCL_LANGUAGE_VERSION",
                    "__SYCL_DEVICE_ONLY__",
                    "__SPIR__",
                    "__SPIRV__",
                ]
            self.assertCountEqual(p.defines, expected)

    def test_nvcc(self):
        """compilers/nvcc"""
        argv = [
            "nvcc",
            "-fopenmp",
            "--gpu-architecture=compute_70",
            "--gpu-code=compute_70,sm_70,sm_75",
            "test.cpp",
        ]

        parser = ArgumentParser(argv[0])

        passes = parser.parse_args(argv[1:])

        pass_names = {p.pass_name for p in passes}
        self.assertCountEqual(pass_names, {"default", "sm_70", "sm_75"})

        defaults = ["__NVCC__", "__CUDACC__"]
        for p in passes:
            if p.pass_name == "default":
                expected = defaults + ["_OPENMP"]
            elif p.pass_name == "sm_70":
                expected = defaults + ["__CUDA_ARCH__=700"]
            elif p.pass_name == "sm_75":
                expected = defaults + ["__CUDA_ARCH__=750"]
            self.assertCountEqual(p.defines, expected)

    def test_user_options(self):
        """Check that we import user-defined options"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write('[compiler."c++"]\n')
            f.write('options = ["-D", "ASDF"]\n')
        config._load_compilers()

        argv = [
            "c++",
            "test.cpp",
        ]

        parser = ArgumentParser(argv[0])
        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 1)
        self.assertCountEqual(passes[0].defines, ["ASDF"])

        tmp.cleanup()

    def test_user_alias(self):
        """Check that we import user-defined aliases"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write('[compiler."c++"]\n')
            f.write('alias_of = "clang"\n')
        config._load_compilers()

        parser = ArgumentParser("c++")
        passes = parser.parse_args(["-fopenmp", "test.cpp"])

        self.assertEqual(len(passes), 1)
        self.assertCountEqual(passes[0].defines, ["_OPENMP"])

        tmp.cleanup()

    def test_nested_aliases(self):
        """Check that we handle user-defined aliases to aliases"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write('[compiler."c++"]\n')
            f.write('alias_of = "g++"\n')
        config._load_compilers()

        parser = ArgumentParser("c++")
        passes = parser.parse_args(["-fopenmp", "test.cpp"])

        self.assertEqual(len(passes), 1)
        self.assertCountEqual(passes[0].defines, ["_OPENMP"])

        tmp.cleanup()

    def test_alias_loops(self):
        """Check that we identify and complain about alias loops"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write("[compiler.foo]\n")
            f.write('alias_of = "bar"\n')
            f.write("[compiler.bar]\n")
            f.write('alias_of = "foo"\n')
        config._load_compilers()

        logging.disable(logging.NOTSET)
        with self.assertLogs("codebasin", level=logging.ERROR):
            _ = ArgumentParser("foo")
        logging.disable()

        tmp.cleanup()

    def test_user_parser(self):
        """Check that we import user-defined parser"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write('[[compiler."c++".parser]]\n')
            f.write('flags = ["-fasdf"]\n')
            f.write('action = "append_const"\n')
            f.write('dest = "passes"\n')
            f.write('const = "asdf-pass"\n')
            f.write('[[compiler."c++".modes]]\n')
            f.write('name = "asdf-mode"\n')
            f.write('defines = ["ASDF"]\n')
            f.write('[[compiler."c++".passes]]\n')
            f.write('name = "asdf-pass"\n')
            f.write('modes = ["asdf-mode"]\n')

        config._load_compilers()

        parser = ArgumentParser("c++")
        passes = parser.parse_args(["-fasdf", "test.cpp"])

        self.assertEqual(len(passes), 2)
        pass_names = {p.pass_name for p in passes}
        self.assertCountEqual(pass_names, {"default", "asdf-pass"})

        for p in passes:
            if p.pass_name == "default":
                expected = []
            elif p.pass_name == "asdf-pass":
                expected = ["ASDF"]
            self.assertCountEqual(p.defines, expected)

        tmp.cleanup()

    def test_user_overrides(self):
        """Check that we can merge user-defined overrides"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write('[[compiler."g++".parser]]\n')
            f.write('flags = ["-fopenmp"]\n')
            f.write('action = "append_const"\n')
            f.write('dest = "passes"\n')
            f.write('const = "new-openmp-pass"\n')
            f.write("\n")
            f.write('[[compiler."g++".passes]]\n')
            f.write('name = "new-openmp-pass"\n')
            f.write('modes = ["new-openmp-mode"]\n')
            f.write("\n")
            f.write('[[compiler."g++".modes]]\n')
            f.write('name = "new-openmp-mode"\n')
            f.write('defines = ["_NEW_OPENMP"]\n')
            f.write("\n")
            f.write('[compiler."g++"]\n')
            f.write('options = ["-D", "EXTRA_DEFINE"]\n')
            f.write("\n")
            f.write("[[compiler.clang.modes]]\n")
            f.write('name = "openmp"\n')
            f.write("defines = []\n")
            f.write("\n")
            f.write("[[compiler.icx.passes]]\n")
            f.write('name = "sycl-spir64"\n')
            f.write("defines = []\n")
            f.write("\n")
            f.write("[compiler.nvcc]\n")
            f.write('alias_of = "unknown"\n')

        # Verify that the correct warnings are generated when loading the file.
        logging.disable(logging.NOTSET)
        with self.assertLogs("codebasin", level=logging.WARNING) as cm:
            config._load_compilers()
        logging.disable()

        self.assertEqual(
            cm.output,
            [
                "WARNING:codebasin.config:definition of g++ in .cbi/config overrides alias.",
                "WARNING:codebasin.config:compiler mode 'openmp' redefined",
                "WARNING:codebasin.config:compiler pass 'sycl-spir64' redefined",
                "WARNING:codebasin.config:nvcc redefined as alias of unknown.",
            ],
        )

        # Verify that user-defined overrides affect passes, etc.
        parser = ArgumentParser("g++")
        argv = ["-fopenmp"]
        passes = parser.parse_args(argv)

        pass_names = {p.pass_name for p in passes}
        self.assertCountEqual(pass_names, {"default", "new-openmp-pass"})

        for p in passes:
            if p.pass_name == "default":
                expected = ["EXTRA_DEFINE"]
            else:
                expected = ["EXTRA_DEFINE", "_NEW_OPENMP"]
            self.assertCountEqual(p.defines, expected)

        # Verify that invalid aliases are identified.
        logging.disable(logging.NOTSET)
        with self.assertLogs("codebasin", level=logging.ERROR) as cm:
            _ = ArgumentParser("nvcc")
        logging.disable()

        self.assertEqual(
            cm.output,
            [
                "ERROR:codebasin.config:Compiler 'nvcc' aliases unrecognized 'unknown'.",
            ],
        )

        tmp.cleanup()

    def test_unrecognized(self):
        """Check that we report unrecognized compilers, modes and passes."""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write("[[compiler.foo.parser]]\n")
            f.write('flags = ["-pass"]\n')
            f.write('action = "append_const"\n')
            f.write('dest = "passes"\n')
            f.write('const = "unrecognized-pass"\n')
            f.write("[[compiler.foo.parser]]\n")
            f.write('flags = ["-mode"]\n')
            f.write('action = "append_const"\n')
            f.write('dest = "modes"\n')
            f.write('const = "unrecognized-mode"\n')
        config._load_compilers()

        logging.disable(logging.NOTSET)
        with self.assertLogs("codebasin", level=logging.WARNING) as cm:
            _ = ArgumentParser("foo").parse_args(
                ["-pass", "-mode", "-unrecognized"],
            )
        logging.disable()

        self.assertCountEqual(
            cm.output,
            [
                "WARNING:codebasin.config:Unrecognized arguments: '-unrecognized'",
                "ERROR:codebasin.config:Unrecognized compiler pass: unrecognized-pass",
                "ERROR:codebasin.config:Unrecognized compiler mode: unrecognized-mode",
            ],
        )

        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
