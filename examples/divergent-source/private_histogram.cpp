// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
#include <cassert>

#include "histogram.h"

void compute_histogram(int N, int* input, int B, int* histogram)
{
    #pragma omp parallel for reduction(+:histogram[0:B])
    for (int i = 0; i < N; i += 16)
    {
        #pragma omp simd simdlen(16)
        for (int v = 0; v < 16; ++v)
        {
            int b = (i + v) % B;
            #pragma omp ordered simd overlap(b)
            {
                histogram[b]++;
            }
        }
    }
}
