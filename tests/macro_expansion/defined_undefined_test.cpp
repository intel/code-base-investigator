// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause

#define CPU 1
#define GPU 2

#define ARCH GPU

#undef CPU
#undef GPU

#if ARCH == 1

void my_cpu_func() {

}

#elif ARCH == 2

void my_gpu_func() {

}

#else

#warning "ARCH Value is unexpected."

#endif

