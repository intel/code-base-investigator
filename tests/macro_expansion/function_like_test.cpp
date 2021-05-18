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

#if defined(GPU)
#define ARCH AGPU
#elif defined(CPU)
#define ARCH ACPU
#endif

#define AGPU_WIDTH 32
#define ACPU_WIDTH 16
#define THE_WIDTH_IMPL(X) X ## _WIDTH

#define THE_WIDTH(X) THE_WIDTH_IMPL(X)

#if THE_WIDTH(ARCH) == 32
#warn "That's a wide width"
#endif

#if THE_WIDTH(ARCH) == 16
#warn "That's a wide width"
#warn "But not as much"
#endif
