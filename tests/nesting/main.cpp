// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#define NESTING_TEST

#ifdef CPU
int foo()
{
#ifdef NESTING_TEST
    return 0;
#endif
}
#endif

#ifdef GPU
int bar()
{
#ifdef NESTING_TEST
    return 1;
#endif
}
#endif
