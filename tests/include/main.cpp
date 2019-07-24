// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#include <cstdio>
#include <cstdlib>

#include "test.h"
#include "test.h"    // repeated include to test handling of guards
#include "missing.h" // missing include to test file handling

#include COMPUTED_INCLUDE

void main(int argc, char* argv[])
{
    return 0;
}
