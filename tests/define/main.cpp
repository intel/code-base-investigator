// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#define SOURCE_DEFINE
#ifdef SOURCE_DEFINE
int foo() // This version should be counted
{
    return 0;
}
#endif

#undef SOURCE_DEFINE
#ifdef SOURCE_DEFINE
int bar() // This version should not
{
    return 1;
}
#endif
