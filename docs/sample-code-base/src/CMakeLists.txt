# Copyright (c) 2024 Intel Corporation
# SPDX-License-Identifier: 0BSD
cmake_minimum_required(VERSION 3.5)
project(tutorial)

set(SOURCES main.cpp third-party/library.cpp)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(GPU_OFFLOAD "Enable GPU offload." OFF)
if (GPU_OFFLOAD)
    add_definitions("-D GPU_OFFLOAD=1")
    list(APPEND SOURCES gpu/foo.cpp)
else()
    list(APPEND SOURCES cpu/foo.cpp)
endif()

add_executable(tutorial ${SOURCES})
