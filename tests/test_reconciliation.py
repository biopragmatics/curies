"""Tests for reconciliation."""

import unittest

from curies import Converter, Record, remap_curie_prefixes, remap_uri_prefixes, rewire

#: The beginning of URIs used throughout examples
P = "https://example.org"


class TestCURIERemapping(unittest.TestCase):
    """A test case for CURIE prefix remapping."""

    def test_transitive_error(self):
        """Test error on transitive remapping."""
        converter = Converter([])
        curie_remapping = {"b": "c", "c": "d"}
        with self.assertRaises(NotImplementedError):
            remap_curie_prefixes(converter, curie_remapping)

    def test_missing(self):
        """Test simple upgrade."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix=f"{P}/a/"),
        ]
        converter = Converter(records)
        curie_remapping = {"b": "c"}
        converter = remap_curie_prefixes(converter, curie_remapping)
        self.assertEqual(records, converter.records)

    def test_simple(self):
        """Test simple upgrade."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix=f"{P}/a/"),
        ]
        converter = Converter(records)
        curie_remapping = {"a": "a1"}
        converter = remap_curie_prefixes(converter, curie_remapping)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(prefix="a1", prefix_synonyms=["a", "x"], uri_prefix=f"{P}/a/"),
            converter.records[0],
        )

    def test_synonym(self):
        """Test that an upgrade configuration that would cause a clash does nothing."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix=f"{P}/a/"),
        ]
        converter = Converter(records)
        curie_remapping = {"a": "x"}
        converter = remap_curie_prefixes(converter, curie_remapping)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(prefix="x", prefix_synonyms=["a"], uri_prefix=f"{P}/a/"),
            converter.records[0],
        )

    def test_clash(self):
        """Test that an upgrade configuration that would cause a clash does nothing."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix=f"{P}/a/"),
            Record(prefix="b", prefix_synonyms=["y"], uri_prefix=f"{P}/b/"),
        ]
        converter = Converter(records)
        curie_remapping = {"a": "b"}
        converter = remap_curie_prefixes(converter, curie_remapping)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(records, converter.records)

    def test_clash_synonym(self):
        """Test a clash on a synonym."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix=f"{P}/a/"),
            Record(prefix="b", prefix_synonyms=["y"], uri_prefix=f"{P}/b/"),
        ]
        converter = Converter(records)
        curie_remapping = {"a": "y"}
        converter = remap_curie_prefixes(converter, curie_remapping)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(records, converter.records)


class TestURIRemapping(unittest.TestCase):
    """A test case for URI prefix remapping."""

    def test_transitive_error(self):
        """Test error on transitive remapping."""
        converter = Converter([])
        uri_remapping = {f"{P}/nope/": f"{P}/more-nope/", f"{P}/more-nope/": f"{P}/more-more-nope/"}
        with self.assertRaises(NotImplementedError) as e:
            remap_uri_prefixes(converter, uri_remapping)

        # check that stringification works
        self.assertIn("75", str(e.exception))

    def test_missing(self):
        """Test simple upgrade."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/"),
        ]
        converter = Converter(records)
        uri_remapping = {f"{P}/nope/": f"{P}/more-nope/"}
        converter = remap_uri_prefixes(converter, uri_remapping)
        self.assertEqual(records, converter.records)

    def test_simple(self):
        """Test simple upgrade."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/", uri_prefix_synonyms=[f"{P}/a1/"]),
        ]
        converter = Converter(records)
        uri_remapping = {f"{P}/a/": f"{P}/a2/"}
        converter = remap_uri_prefixes(converter, uri_remapping)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(
                prefix="a",
                uri_prefix=f"{P}/a2/",
                uri_prefix_synonyms=[f"{P}/a/", f"{P}/a1/"],
            ),
            converter.records[0],
        )

    def test_synonym(self):
        """Test that an upgrade configuration that would cause a clash does nothing."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/", uri_prefix_synonyms=[f"{P}/a1/"]),
        ]
        converter = Converter(records)
        uri_remapping = {f"{P}/a1/": f"{P}/a2/"}
        converter = remap_uri_prefixes(converter, uri_remapping)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(prefix="a", uri_prefix=f"{P}/a2/", uri_prefix_synonyms=[f"{P}/a/", f"{P}/a1/"]),
            converter.records[0],
        )

    def test_clash_preferred(self):
        """Test that an upgrade configuration that would cause a clash does nothing."""
        records = [
            Record(prefix="a", prefix_synonyms=["x"], uri_prefix=f"{P}/a/"),
            Record(prefix="b", prefix_synonyms=["y"], uri_prefix=f"{P}/b/"),
        ]
        converter = Converter(records)
        upgrades = {f"{P}/a/": f"{P}/b/"}
        converter = remap_uri_prefixes(converter, upgrades)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(records, converter.records)

    def test_clash_synonym(self):
        """Test clashing with a synonym."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/"),
            Record(prefix="b", uri_prefix=f"{P}/b/", uri_prefix_synonyms=[f"{P}/b1/"]),
        ]
        converter = Converter(records)
        upgrades = {f"{P}/a/": f"{P}/b1/"}
        converter = remap_uri_prefixes(converter, upgrades)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(records, converter.records)


class TestRewire(unittest.TestCase):
    """A test case for rewiring."""

    def test_idempotent(self):
        """Test that a redundant rewiring doesn't do anything."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/", uri_prefix_synonyms=["https://a.org/"]),
        ]
        converter = Converter(records)
        rewiring = {"a": f"{P}/a/"}
        converter = rewire(converter, rewiring)
        self.assertEqual(records, converter.records)

    def test_upgrade_uri_prefixes_simple(self):
        """Test simple upgrade."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/", uri_prefix_synonyms=["https://a.org/"]),
        ]
        converter = Converter(records)
        rewiring = {"a": f"{P}/a1/"}
        converter = rewire(converter, rewiring)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            Record(
                prefix="a", uri_prefix=f"{P}/a1/", uri_prefix_synonyms=["https://a.org/", f"{P}/a/"]
            ),
            converter.records[0],
        )

    # def test_upgrade_uri_prefixes_add(self):
    #     """Test an upgrade that adds an extra prefix."""
    #     records = [
    #         Record(prefix="a", uri_prefix=f"{P}/a/"),
    #     ]
    #     converter = Converter(records)
    #     rewiring = {"b": f"{P}/b/"}
    #     converter = rewire(converter, rewiring)
    #     self.assertEqual(2, len(converter.records))
    #     self.assertEqual(
    #         [
    #             Record(prefix="a", uri_prefix=f"{P}/a/"),
    #             Record(prefix="b", uri_prefix=f"{P}/b/"),
    #         ],
    #         converter.records,
    #     )

    def test_upgrade_uri_prefixes_clash(self):
        """Test an upgrade that does nothing since it would create a clash."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/"),
            Record(prefix="b", uri_prefix=f"{P}/b/"),
        ]
        converter = Converter(records)
        rewiring = {"b": f"{P}/a/"}
        converter = rewire(converter, rewiring)
        self.assertEqual(2, len(converter.records))
        self.assertEqual(
            [
                Record(prefix="a", uri_prefix=f"{P}/a/"),
                Record(prefix="b", uri_prefix=f"{P}/b/"),
            ],
            converter.records,
        )

    def test_upgrade_uri_upgrade(self):
        """Test an upgrade of an existing URI prefix synonym."""
        records = [
            Record(prefix="a", uri_prefix=f"{P}/a/", uri_prefix_synonyms=[f"{P}/a1/"]),
        ]
        converter = Converter(records)
        rewiring = {"a": f"{P}/a1/"}
        converter = rewire(converter, rewiring)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            [
                Record(
                    prefix="a",
                    uri_prefix=f"{P}/a1/",
                    uri_prefix_synonyms=[f"{P}/a/"],
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
                uri_prefix=f"{P}/a/",
                uri_prefix_synonyms=[f"{P}/a1/"],
            ),
        ]
        converter = Converter(records)
        rewiring = {"a1": f"{P}/a1/"}
        converter = rewire(converter, rewiring)
        self.assertEqual(1, len(converter.records))
        self.assertEqual(
            [
                Record(
                    prefix="a",
                    prefix_synonyms=["a1"],
                    uri_prefix=f"{P}/a1/",
                    uri_prefix_synonyms=[f"{P}/a/"],
                ),
            ],
            converter.records,
        )
