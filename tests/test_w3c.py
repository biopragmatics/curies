"""Tests for W3C utilities."""

import unittest
from pathlib import Path

from curies.api import curie_is_w3c

HERE = Path(__file__).parent.resolve()
RESOURCES = HERE.joinpath("resources")
VALID_CURIES_PATH = RESOURCES.joinpath("valid_curies.txt")
INVALID_CURIES_PATH = RESOURCES.joinpath("invalid_curies.txt")


class TestW3C(unittest.TestCase):
    """Tests for W3C utilities."""

    def test_valid_curies(self):
        """Test validating CURIEs."""
        for curie in VALID_CURIES_PATH.read_text().splitlines():
            with self.subTest(curie=curie):
                self.assertTrue(curie_is_w3c(curie))

    def test_invalid_curies(self):
        """Test validating CURIEs.

        .. todo::

            Later, extend this to the following:

            1. ``pfx://abc``
            2. ``pfx://``
            3. ``://``
            4. ``/``
        """
        for curie in INVALID_CURIES_PATH.read_text().splitlines():
            with self.subTest(curie=curie):
                self.assertFalse(curie_is_w3c(curie))
