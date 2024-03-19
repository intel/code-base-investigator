// Copyright (c) 2024 Intel Corporation
// SPDX-License-Identifier: 0BSD
#include <cstdio>

void foo() {
#if __GNUC__ >= 13
    printf("Using a feature that is only available in GCC 13 and later.\n");
#endif
    printf("Running the rest of foo() on the CPU.\n");
}
