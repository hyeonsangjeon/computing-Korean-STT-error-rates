"""Keep Python 3.8 source builds while using SPDX on modern builders."""

import sys

from setuptools import setup


if sys.version_info < (3, 9):
    # The last setuptools for Python 3.8 predates PEP 639.
    setup(license="MIT")
else:
    setup(license_expression="MIT")
