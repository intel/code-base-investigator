! Copyright (C) 2019-2020 Intel Corporation
! SPDX-License-Identifier: BSD-3-Clause

program foo

#define my_fortran_macro() \
  /*wow a comment*/ \
  a = b - c /* another */ \
  + b !FOO  // "neat" /* hey look a c comment*/

  integer a,b,c
  b = b  & ! Comments after continuations
       ! no comment!
           + b
  !$ A directive

  write(*,*) "Fortran! /*Has*/ !Unique parsing semantics"
  !omp$ a different directive
  write(*,*) "& Fortran! has complex ways of dealing with (&) //ampersands&"
  !omp5% not a directives
  write(*,*) "Fortran! \& d \n &
                                !Can be "
       &'quite' complex&
       !Mixin
&"//"&
       !Mixin
       &with quoted continuations"

my_fortran_macro()

#if !defined(GPU) /*something*/
  write(*,*) "directives" // "appending"
#endif
end program foo
