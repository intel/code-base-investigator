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

    def test_clang(self):
        """compilers/clang"""
        args = ["clang", "-fsycl-is-device", "test.cpp"]

        compiler = config.recognize_compiler(args)
        self.assertTrue(type(compiler) is config.ClangCompiler)

        passes = compiler.get_passes()
        self.assertEqual(passes, {"default"})

        self.assertTrue(compiler.has_implicit_behavior("default"))
        defines = compiler.get_defines("default")
        self.assertEqual(defines, ["__SYCL_DEVICE_ONLY__"])

    def test_intel_sycl(self):
        """compilers/intel_sycl"""
        args = ["icpx", "-fsycl", "test.cpp"]

        compiler = config.recognize_compiler(args)
        self.assertTrue(type(compiler) is config.IntelCompiler)

        passes = compiler.get_passes()
        self.assertEqual(passes, {"default", "spir64"})

        expected = ["__SYCL_DEVICE_ONLY__", "__SPIR__", "__SPIRV__"]
        self.assertTrue(compiler.has_implicit_behavior("spir64"))
        defines = compiler.get_defines("spir64")
        self.assertEqual(defines, expected)

    def test_intel_targets(self):
        """compilers/intel_targets"""
        args = [
            "icpx",
            "-fsycl",
            "-fsycl-targets=spir64,x86_64",
            "-fopenmp",
            "test.cpp",
        ]

        compiler = config.recognize_compiler(args)
        self.assertTrue(type(compiler) is config.IntelCompiler)

        passes = compiler.get_passes()
        self.assertEqual(passes, {"default", "spir64", "x86_64"})

        self.assertTrue(compiler.has_implicit_behavior("default"))
        defines = compiler.get_defines("default")
        self.assertEqual(defines, ["_OPENMP"])

        expected = ["__SYCL_DEVICE_ONLY__", "__SPIR__", "__SPIRV__"]
        self.assertTrue(compiler.has_implicit_behavior("spir64"))
        defines = compiler.get_defines("spir64")
        self.assertEqual(defines, expected)
        self.assertTrue(compiler.has_implicit_behavior("x86_64"))
        defines = compiler.get_defines("x86_64")
        self.assertEqual(defines, expected)

    def test_nvcc(self):
        """compilers/nvcc"""
        args = [
            "nvcc",
            "--gpu-architecture=compute_50",
            "--gpu-code=compute_50,sm_50,sm_52",
            "test.cpp",
        ]

        compiler = config.recognize_compiler(args)
        self.assertTrue(type(compiler) is config.NvccCompiler)

        passes = compiler.get_passes()
        self.assertEqual(passes, {"default", "50", "52"})

        defaults = ["__NVCC__", "__CUDACC__"]
        self.assertTrue(compiler.has_implicit_behavior("default"))
        defines = compiler.get_defines("default")
        self.assertEqual(defines, defaults)

        self.assertTrue(compiler.has_implicit_behavior("50"))
        defines = compiler.get_defines("50")
        self.assertEqual(defines, defaults + ["__CUDA_ARCH__=500"])

        self.assertTrue(compiler.has_implicit_behavior("52"))
        defines = compiler.get_defines("52")
        self.assertEqual(defines, defaults + ["__CUDA_ARCH__=520"])

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

        args = [
            "c++",
            "test.cpp",
        ]

        compiler = config.recognize_compiler(args)
        defines = compiler.get_defines("default")
        self.assertCountEqual(defines, ["ASDF"])

        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
