// Copyright (C) 2019 Intel Corporation
// SPDX-License-Identifier: BSD-3-Clause
//
// This test should result in 4 Nodes. One FileNode with three children. The Children are a CodeNode, followed by a DefineNode, followed by another CodeNode.

void defines_and_comments() {

#define FOO 1
/* *****
#define FOO 0
#define BAR 2
#define BAZ 3
 * ******/
}
