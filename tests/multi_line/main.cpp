// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#define FOO 0
#define BAR 10

#if FOO < 1 \
    && BAR == 10
int foo()
{
    return 0;
}
#endif

#if FOO == 1 \
    && BAR >= 2
int bar()
{
    return 1;
}
#endif

/\
*
*/ # /*
*/ defi\
ne FO\
O 10\
20
