"""Tests for reconciliation."""

import unittest

from curies import Record, Converter, remap_curie_prefixes, rewire


class TestReconciliation(unittest.TestCase):
    """A test case for reconciliation."""

    def test_upgrade_curie_prefixes_missing(self):
        """Test simple upgrade."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix="https://example.org/a/"),
        ]
        converter = Converter(records)
        upgrades = {"b": "c"}
        converter = remap_curie_prefixes(converter, upgrades)
        self.assertEqual(records, converter.records)

    def test_upgrade_curie_prefixes_simple(self):
        """Test simple upgrade."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix="https://example.org/a/"),
        ]
        converter = Converter(records)
        upgrades = {"a": "a1"}
        converter = remap_curie_prefixes(converter, upgrades)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(prefix="a1", prefix_synonyms=["a", "x"], uri_prefix="https://example.org/a/"),
            converter.records[0],
        )

    def test_upgrade_curie_prefixes_clash(self):
        """Test that an upgrade configuration that would cause a clash does nothing."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix="https://example.org/a/"),
            Record(prefix="b", prefix_synonyms=["y"], uri_prefix="https://example.org/b/"),
        ]
        converter = Converter(records)
        upgrades = {"a": "b"}
        converter = remap_curie_prefixes(converter, upgrades)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(records, converter.records)

    def test_upgrade_curie_prefixes_synonym(self):
        """Test that an upgrade configuration that would cause a clash does nothing."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix="https://example.org/a/"),
        ]
        converter = Converter(records)
        upgrades = {"a": "x"}
        converter = remap_curie_prefixes(converter, upgrades)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(prefix="x", prefix_synonyms=["a"], uri_prefix="https://example.org/a/"),
            converter.records[0],
        )

    def test_upgrade_uri_prefixes_simple(self):
        """Test simple upgrade."""
        records = [
            Record(
                prefix="a",
                uri_prefix="https://example.org/a/",
                uri_prefix_synonyms=["https://a.org/"],
            ),
        ]
        converter = Converter(records)
        upgrades = {"a": "https://example.org/a1/"}
        converter = rewire(converter, upgrades)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(
                prefix="a",
                uri_prefix="https://example.org/a1/",
                uri_prefix_synonyms=["https://a.org/", "https://example.org/a/"],
            ),
            converter.records[0],
        )

    def test_upgrade_uri_prefixes_add(self):
        """Test an upgrade that adds an extra prefix."""
        records = [
            Record(prefix="a", uri_prefix="https://example.org/a/"),
        ]
        converter = Converter(records)
        upgrades = {"b": "https://example.org/b/"}
        converter = rewire(converter, upgrades)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(
            [
                Record(prefix="a", uri_prefix="https://example.org/a/"),
                Record(prefix="b", uri_prefix="https://example.org/b/"),
            ],
            converter.records,
        )

    def test_upgrade_uri_prefixes_clash(self):
        """Test an upgrade that does nothing since it would create a clash."""
        records = [
            Record(prefix="a", uri_prefix="https://example.org/a/"),
            Record(prefix="b", uri_prefix="https://example.org/b/"),
        ]
        converter = Converter(records)
        upgrades = {"b": "https://example.org/a/"}
        converter = rewire(converter, upgrades)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(
            [
                Record(prefix="a", uri_prefix="https://example.org/a/"),
                Record(prefix="b", uri_prefix="https://example.org/b/"),
            ],
            converter.records,
        )

    def test_upgrade_uri_upgrade(self):
        """Test an upgrade of an existing URI prefix synonym."""
        records = [
            Record(
                prefix="a",
                uri_prefix="https://example.org/a/",
                uri_prefix_synonyms=["https://example.org/a1/"],
            ),
        ]
        converter = Converter(records)
        upgrades = {"a": "https://example.org/a1/"}
        converter = rewire(converter, upgrades)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            [
                Record(
                    prefix="a",
                    uri_prefix="https://example.org/a1/",
                    uri_prefix_synonyms=["https://example.org/a/"],
                ),
            ],
            converter.records,
        )

    def test_upgrade_uri_upgrade_with_curie_prefix(self):
        """Test an upgrade of an existing URI prefix synonym via a CURIE prefix synonym."""
        records = [
            Record(
                prefix="a",
                prefix_synonyms=["a1"],
                uri_prefix="https://example.org/a/",
                uri_prefix_synonyms=["https://example.org/a1/"],
            ),
        ]
        converter = Converter(records)
        upgrades = {"a1": "https://example.org/a1/"}
        converter = rewire(converter, upgrades)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            [
                Record(
                    prefix="a",
                    prefix_synonyms=["a1"],
                    uri_prefix="https://example.org/a1/",
                    uri_prefix_synonyms=["https://example.org/a/"],
                ),
            ],
            converter.records,
        )
