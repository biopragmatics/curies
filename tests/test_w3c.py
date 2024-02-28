"""Tests for W3C utilities."""

import unittest
from pathlib import Path

from curies.w3c import curie_is_w3c

HERE = Path(__file__).parent.resolve()
RESOURCES = HERE.joinpath("resources")
VALID_CURIES_PATH = RESOURCES.joinpath("valid_curies.txt")
INVALID_CURIES_PATH = RESOURCES.joinpath("invalid_curies.txt")


class TestW3C(unittest.TestCase):
    """Tests for W3C utilities."""

    def test_validating_curies(self):
        """Test validating CURIEs."""
        for curie in VALID_CURIES_PATH.read_text().splitlines():
            with self.subTest(curie=curie):
                self.assertTrue(curie_is_w3c(curie))
        for curie in INVALID_CURIES_PATH.read_text().splitlines():
            with self.subTest(curie=curie):
                self.assertFalse(curie_is_w3c(curie))
