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

#ifdef USE_OFFLOAD
    #pragma omp target enter data map(alloc:input[0:N], histogram[0:B])
    #pragma omp target update to(input[0:N], histogram[0:B])
#endif

    compute_histogram(N, input, B, histogram);

#ifdef USE_OFFLOAD
    #pragma omp target update from(histogram[0:B])
    #pragma omp target exit data map(delete:input[0:N], histogram[0:B])
#endif

    for (int j = 0; j < B; ++j)
    {
        printf("histogram[%d] = %d\n", j, histogram[j]);
    }

    free(histogram);
    free(input);

    return 0;
}
