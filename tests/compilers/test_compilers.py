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
        config._importcfg = None
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


if __name__ == "__main__":
    unittest.main()
