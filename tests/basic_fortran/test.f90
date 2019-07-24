! Copyright (C) 2019 Intel Corporation
! SPDX-License-Identifier: BSD-3-Clause

program test
      implicit none
      integer :: i

      ! There are 3 source lines above this counted to both platforms
      ! And 3 directives that count to both platforms (below)
#if defined(GPU)
      ! 3 lines here count for the GPU
      i = 1
      i = i + i
      i = i * i
#elif defined(CPU)
      ! 2 lines here count for the CPU
      i = 2
      i = i**i
!#else
!     The above else should be ignored
!     i = -1
#endif

      ! 2 more source lines to both platforms.
      write(6,*) 'i = ', i
end program test
