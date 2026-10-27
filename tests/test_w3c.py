"""Test W3C validation."""

import csv
import unittest
from pathlib import Path

from curies.w3c import CURIE_RE, is_w3c_curie, is_w3c_prefix

HERE = Path(__file__).parent.resolve()
DIRECTORY = HERE.joinpath("resources")
VALID_CURIES_PATH = DIRECTORY.joinpath("valid_curies.tsv")
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
        with VALID_CURIES_PATH.open() as file:
            reader = csv.DictReader(file, delimiter="\t")
            for row, record in enumerate(reader, start=2):
                curie = record["curie"]
                with self.subTest(row=row, description=record["description"]):
                    self.assertTrue(
                        is_w3c_curie(curie), msg="CURIE should test as valid, but did not"
                    )

                    curie_match = CURIE_RE.match(curie)
                    if curie_match is None:
                        self.fail(f"match was none on {curie=}")
                    self.assertEqual(
                        record["prefix"] or None,
                        curie_match.group("prefix"),
                        msg=f"{row=} failed to parse prefix in {curie=}. {curie_match.groupdict()=}",
                    )
                    self.assertEqual(
                        record["identifier"],
                        curie_match.group("identifier"),
                        msg=f"{row=} failed to parse ID in {curie=}. {curie_match=}",
                    )

        for curie in _read(INVALID_CURIES_PATH):
            with self.subTest(curie=curie):
                self.assertFalse(
                    is_w3c_curie(curie), msg="CURIE should test as invalid, but did not"
                )
