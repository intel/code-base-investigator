// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
#include <cstdio>
#include <cstdlib>

int main(int argc, char* argv[])
{
    if (argc != 2)
    {
        printf("Usage: histogram [use_offload]\n");
        return -1;
    }
    int use_offload = atoi(argv[1]);

    int N = 1024;
    int B = 16;
    printf("Computing histogram of %d inputs and %d bins\n", N, B);
    printf("use_offload = %s\n", use_offload ? "true" : "false");

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

    #pragma omp target enter data map(alloc:input[0:N], histogram[0:B]) if (use_offload > 0)
    #pragma omp target update to(input[0:N], histogram[0:B]) if (use_offload > 0)

    #pragma omp target teams distribute parallel for simd if (target: use_offload > 0)
    for (int i = 0; i < N; ++i)
    {
        int b = i % B;
        #pragma omp atomic
        histogram[b]++;
    }

    #pragma omp target update from(histogram[0:B]) if (use_offload > 0)

    #pragma omp target exit data map(delete:input[0:N], histogram[0:B]) if (use_offload > 0)

    for (int j = 0; j < B; ++j)
    {
        printf("histogram[%d] = %d\n", j, histogram[j]);
    }

    free(histogram);
    free(input);

    return 0;
}
