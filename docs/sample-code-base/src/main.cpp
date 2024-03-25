// Copyright (c) 2024 Intel Corporation
// SPDX-License-Identifier: 0BSD
#include <cstdio>
#include "third-party/library.h"
void foo();

int main(int argc, char* argv[])
{
#if !defined(GPU_OFFLOAD)
    printf("Running on the CPU.\n");
#else
    printf("Running on the GPU.\n");
#endif
    foo();
    bar();
}
