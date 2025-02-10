# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import tempfile
import unittest
from pathlib import Path

from codebasin import config


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
        args = config._parse_compiler_args(argv)
        self.assertEqual(
            args.defines,
            ["MACRO", "FUNCTION_MACRO=1", "MACRO_AFTER_SPACE"],
        )
        self.assertEqual(
            args.include_paths,
            ["/path", "/path/after/space", "/system/path"],
        )
        self.assertEqual(args.include_files, ["foo.inc", "bar.inc"])

    def test_gnu(self):
        """compilers/gnu"""
        argv = ["g++", "-fopenmp", "test.cpp"]

        parser = config.recognize_compiler(argv[0])
        self.assertTrue(type(parser) is config.GnuArgumentParser)

        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 1)

        self.assertEqual(passes[0].pass_name, "default")

        defines = passes[0].defines
        self.assertEqual(defines, ["_OPENMP"])

    def test_clang(self):
        """compilers/clang"""
        argv = ["clang", "-fsycl-is-device", "test.cpp"]

        parser = config.recognize_compiler(argv[0])
        self.assertTrue(type(parser) is config.ClangArgumentParser)

        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 1)

        self.assertEqual(passes[0].pass_name, "default")

        defines = passes[0].defines
        self.assertEqual(defines, ["__SYCL_DEVICE_ONLY__"])

    def test_intel_sycl(self):
        """compilers/intel_sycl"""
        argv = ["icpx", "-fsycl", "test.cpp"]

        parser = config.recognize_compiler(argv[0])
        self.assertTrue(type(parser) is config.ClangArgumentParser)

        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 2)

        pass_names = {p.pass_name for p in passes}
        self.assertEqual(pass_names, {"default", "spir64"})

        for p in passes:
            if p.pass_name == "default":
                expected = []
            else:
                expected = ["__SYCL_DEVICE_ONLY__", "__SPIR__", "__SPIRV__"]
            self.assertEqual(p.defines, expected)

    def test_intel_targets(self):
        """compilers/intel_targets"""
        argv = [
            "icpx",
            "-fsycl",
            "-fsycl-targets=spir64,x86_64",
            "-fopenmp",
            "test.cpp",
        ]

        parser = config.recognize_compiler(argv[0])
        self.assertTrue(type(parser) is config.ClangArgumentParser)

        passes = parser.parse_args(argv[1:])

        pass_names = {p.pass_name for p in passes}
        self.assertEqual(pass_names, {"default", "spir64", "x86_64"})

        for p in passes:
            if p.pass_name == "default":
                expected = ["_OPENMP"]
                self.assertEqual(p.defines, ["_OPENMP"])
            elif p.pass_name == "spir64" or p.pass_name == "x86_64":
                expected = ["__SYCL_DEVICE_ONLY__", "__SPIR__", "__SPIRV__"]
            self.assertEqual(p.defines, expected)

    def test_nvcc(self):
        """compilers/nvcc"""
        argv = [
            "nvcc",
            "-fopenmp",
            "--gpu-architecture=compute_50",
            "--gpu-code=compute_50,sm_50,sm_52",
            "test.cpp",
        ]

        parser = config.recognize_compiler(argv[0])
        self.assertTrue(type(parser) is config.NvccArgumentParser)

        passes = parser.parse_args(argv[1:])

        pass_names = {p.pass_name for p in passes}
        self.assertEqual(pass_names, {"default", "50", "52"})

        defaults = ["__NVCC__", "__CUDACC__"]
        for p in passes:
            if p.pass_name == "default":
                expected = defaults + ["_OPENMP"]
            elif p.pass_name == "50":
                expected = defaults + ["__CUDA_ARCH__=500"]
            elif p.pass_name == "52":
                expected = defaults + ["__CUDA_ARCH__=520"]
            self.assertEqual(p.defines, expected)

    def test_user_options(self):
        """Check that we import user-defined options"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)
        os.mkdir(".cbi")
        with open(path / ".cbi" / "config", mode="w") as f:
            f.write('[compiler."c++"]\n')
            f.write('options = ["-D", "ASDF"]\n')
        config.load_importcfg()

        argv = [
            "c++",
            "test.cpp",
        ]

        parser = config.recognize_compiler(argv[0])
        passes = parser.parse_args(argv[1:])
        self.assertEqual(len(passes), 1)
        self.assertCountEqual(passes[0].defines, ["ASDF"])

        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
