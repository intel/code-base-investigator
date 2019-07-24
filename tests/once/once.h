// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#pragma once

#ifdef PROCESSED_ONCE // this should never be true
void foo()
{
    return;
};
#endif
#define PROCESSED_ONCE
