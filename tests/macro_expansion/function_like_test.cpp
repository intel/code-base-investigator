// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#define FOO 1
#define BAR 2

#define MAX(a,b) (a) >= (b) ? (a) : (b)

double a, b;

#if MAX(FOO, BAR) == 0
void neither_foo_nor_bar()
{
    a = b
}
#else
void both_foo_and_bar()
{
    a = 10;
    b = a;
    a = 15;
    return;
}
#endif

#define _GLIBC_PREREQ(x) x

#if _GLIBC_PREREQ(6)
#else
#error "#error "Shouldn't be true"
#endif

#if _UNDEFINED_GLIBC_PREREQ(6)
#else
#error "Shouldn't be true"
#endif
