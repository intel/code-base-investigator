// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
#include <cstdio>
#include <cstdlib>

#include "histogram.h"

int main(int argc, char* argv[])
{
    int N = 1024;
    int B = 16;
    printf("Computing histogram of %d inputs and %d bins\n", N, B);

    int* input = (int*) malloc(N * sizeof(int));
    for (int i = 0; i < N; ++i)
    {
        input[i] = rand() % N;
    }

    int* histogram = (int*) malloc(B * sizeof(int));
    for (int j = 0; j < B; ++j)
    {
        histogram[j] = 0;
    }

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

    for (int j = 0; j < B; ++j)
    {
        printf("histogram[%d] = %d\n", j, histogram[j]);
    }

    free(histogram);
    free(input);

    return 0;
}
