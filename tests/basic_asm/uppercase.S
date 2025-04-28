; Copyright (C) 2021 Intel Corporation
; SPDX-License-Identifier: BSD-3-Clause

    ## Another comment
    // Yet another comment
%define something
.data Something
.globl Name

    mov %r0, %r1
    ;; comment
    pop

LABEL0:
    // that other comment syntax
    add 4(%r0,10,%r1), %r15

    ret
