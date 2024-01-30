# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import warnings

import codebasin.walkers

warnings.warn(
    "Calling codebasin package internals is deprecated. "
    + "Please call the codebasin script directly instead. "
    + "A new, stable, package interface will be introduced in "
    + "a future release of Code Base Investigator.",
    DeprecationWarning,
)
