// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#define BAR 1
#define FOO BAR
#undef BAR
#define BAR FOO

#if FOO == 1
void my_func();
#else
void other_func();
#endif
