// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
#include "histogram.h"

void compute_histogram(int N, int* input, int B, int* histogram)
{
#ifdef USE_OFFLOAD
    #pragma omp target teams distribute parallel for simd
#else
    #pragma omp parallel for simd
#endif
    for (int i = 0; i < N; ++i)
    {
        int b = i % B;
        #pragma omp atomic
        histogram[b]++;
    }
}
