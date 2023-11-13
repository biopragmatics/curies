"""Test discovering a prefix map from a list of URIs."""

import unittest
from typing import ClassVar

from curies import Converter, Record
from curies.discovery import discover


class TestDiscovery(unittest.TestCase):
    """Test discovery of URI prefixes."""

    converter: ClassVar[Converter]

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the test case with a dummy converter."""
        cls.converter = Converter([])

    def test_simple(self):
        """Test a simple case of discovering URI prefixes."""
        uris = [f"http://ran.dom/{i:03}" for i in range(30)]
        converter = discover(self.converter, uris, cutoff=3)
        self.assertEqual([Record(prefix="ns1", uri_prefix="http://ran.dom/")], converter.records)

        converter = discover(self.converter, uris, cutoff=50)
        self.assertEqual([], converter.records)
