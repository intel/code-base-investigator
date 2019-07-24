// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#ifndef _TEST_H_
#define _TEST_H_

#ifdef CPU
int cpu_specialization()
{
    return 0;
}
#else
int gpu_specialization()
{
    return 0;
}
#endif

#endif /* _TEST_H_ */
