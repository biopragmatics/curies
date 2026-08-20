"""Test W3C validation."""

import unittest
from pathlib import Path

from curies.w3c import is_w3c_curie, is_w3c_prefix

HERE = Path(__file__).parent.resolve()
DIRECTORY = HERE.joinpath("resources")
VALID_CURIES_PATH = DIRECTORY.joinpath("valid_curies.txt")
INVALID_CURIES_PATH = DIRECTORY.joinpath("invalid_curies.txt")
VALID_PREFIXES_PATH = DIRECTORY.joinpath("valid_prefixes.txt")
INVALID_PREFIXES_PATH = DIRECTORY.joinpath("invalid_prefixes.txt")


def _read(path: Path) -> list[str]:
    return path.read_text().splitlines()


class TestValidators(unittest.TestCase):
    """Test W3C validation."""

    def test_prefixes(self) -> None:
        """Test prefixes validation."""
        for prefix in _read(VALID_PREFIXES_PATH):
            with self.subTest(prefix=prefix):
                self.assertTrue(is_w3c_prefix(prefix))

        for prefix in _read(INVALID_PREFIXES_PATH):
            with self.subTest(prefix=prefix):
                self.assertFalse(is_w3c_prefix(prefix))

    def test_curies(self) -> None:
        """Test CURIE validation."""
        for curie in _read(VALID_CURIES_PATH):
            with self.subTest(curie=curie):
                self.assertTrue(is_w3c_curie(curie), msg="CURIE should test as valid, but did not")

        for curie in _read(INVALID_CURIES_PATH):
            with self.subTest(curie=curie):
                self.assertFalse(
                    is_w3c_curie(curie), msg="CURIE should test as invalid, but did not"
                )
