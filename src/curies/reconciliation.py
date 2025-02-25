"""Reconciliation."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from collections.abc import Collection, Mapping

from .api import Converter, Record

__all__ = [
    "remap_curie_prefixes",
    "remap_uri_prefixes",
    "rewire",
]

logger = logging.getLogger(__name__)


class TransitiveError(NotImplementedError):
    """An error when transitive mappings appear."""

    def __init__(self, intersection: Collection[str]) -> None:
        """Initialize the exception.

        :param intersection: The strings that appeared both as keys and values in a
            remapping dictionary (either for CURIEs or URIs)
        """
        self.intersection = intersection

    def __str__(self) -> str:
        return (
            f"Transitive mapping has not been implemented. This is being thrown because "
            f"the following appear in both the keys and values of the remapping: {self.intersection}."
            "\n\nSee discussion at https://github.com/cthoyt/curies/issues/75."
        )


def remap_curie_prefixes(converter: Converter, remapping: Mapping[str, str]) -> Converter:
    """Apply CURIE prefix remappings.

    :param converter: A converter
    :param remapping: A mapping from CURIE prefixes to new CURIE prefixes. Old CURIE
        prefixes become synonyms in the records (i.e., they aren't forgotten).

    :returns: An upgraded converter
    """
    ordering = _order_curie_remapping(converter, remapping)
    intersection = set(remapping).intersection(remapping.values())
    records = {r.prefix: r for r in converter.records}

    modified_records = []
    for old, new_prefix in ordering:
        _old = converter.synonym_to_prefix.get(old)
        if _old is None:
            logger.debug(
                "Remapping %s->%s can not be applied because %s does not appear in the converter. Skipping.",
                old,
                new_prefix,
                old,
            )
            continue

        record = records.pop(_old)
        new_record = converter.get_record(new_prefix)
        if new_record is not None and record != new_record:
            logger.debug(
                "Remapping %s->%s would create a clash because of the existing record %r. Skipping.",
                old,
                new_prefix,
                new_record,
            )
        elif old in intersection:
            record.prefix_synonyms = sorted(
                set(record.prefix_synonyms).difference({old, new_prefix})
            )
            record.prefix = new_prefix
        else:
            record.prefix_synonyms = sorted(
                set(record.prefix_synonyms).union({record.prefix}).difference({new_prefix})
            )
            record.prefix = new_prefix
        modified_records.append(record)

    return Converter([*records.values(), *modified_records])


def remap_uri_prefixes(converter: Converter, remapping: Mapping[str, str]) -> Converter:
    """Apply URI prefix remappings.

    :param converter: A converter
    :param remapping: A mapping from URI prefixes to new URI prefixes. Old URI prefixes
        become synonyms in the records (i.e., they aren't forgotten)

    :returns: An upgraded converter

    :raises TransitiveError: If there are any strings that appear in both the key and
        values of the remapping
    """
    intersection = set(remapping).intersection(remapping.values())
    if intersection:
        raise TransitiveError(intersection)

    records = []
    for record in converter.records:
        new_uri_prefix = _get_uri_preferred_or_synonym(record, remapping)
        if new_uri_prefix is None:
            pass  # nothing to upgrade
        elif (
            new_uri_prefix in converter.reverse_prefix_map
            and new_uri_prefix not in record.uri_prefix_synonyms
        ):
            pass  # would create a clash, don't do anything
        else:
            record.uri_prefix_synonyms = sorted(
                set(record.uri_prefix_synonyms)
                .union({record.uri_prefix})
                .difference({new_uri_prefix})
            )
            record.uri_prefix = new_uri_prefix
        records.append(record)
    return Converter(records)


def rewire(converter: Converter, rewiring: Mapping[str, str]) -> Converter:
    """Apply URI prefix upgrades.

    :param converter: A converter
    :param rewiring: A mapping from CURIE prefixes to new URI prefixes. If CURIE
        prefixes are not already in the converter, new records are created. If new URI
        prefixes clash with any existing ones, they are not added.

    :returns: An upgraded converter
    """
    records = []
    for record in converter.records:
        new_uri_prefix = _get_curie_preferred_or_synonym(record, rewiring)
        if new_uri_prefix is None:
            pass  # nothing to upgrade
        elif new_uri_prefix == record.uri_prefix:
            pass  # it's already the preferred prefix, nothing to do
        elif (
            new_uri_prefix in converter.reverse_prefix_map
            and new_uri_prefix not in record.uri_prefix_synonyms
        ):
            logger.debug(
                "Rewiring %r to %s would create a clash because of the existing record %s. Skipping.",
                record,
                new_uri_prefix,
                converter.reverse_prefix_map[new_uri_prefix],
            )
        else:
            record.uri_prefix_synonyms = sorted(
                set(record.uri_prefix_synonyms)
                .union({record.uri_prefix})
                .difference({new_uri_prefix})
            )
            record.uri_prefix = new_uri_prefix
        records.append(record)

    # potential future functionality: add missing records
    # for prefix, new_uri_prefix in rewiring.items():
    #     if prefix not in converter.synonym_to_prefix:
    #         records.append(Record(prefix=prefix, uri_prefix=new_uri_prefix))

    return Converter(records)


def _get_curie_preferred_or_synonym(record: Record, upgrades: Mapping[str, str]) -> str | None:
    if record.prefix in upgrades:
        return upgrades[record.prefix]
    for s in record.prefix_synonyms:
        if s in upgrades:
            return upgrades[s]
    return None


def _get_uri_preferred_or_synonym(record: Record, upgrades: Mapping[str, str]) -> str | None:
    if record.uri_prefix in upgrades:
        return upgrades[record.uri_prefix]
    for s in record.uri_prefix_synonyms:
        if s in upgrades:
            return upgrades[s]
    return None


class DuplicateValues(ValueError):
    """Raised when multiple values in the remapping correspond to the same preferred CURIE prefix."""


class DuplicateKeys(ValueError):
    """Raised when multiple keys in the remapping correspond to the same preferred CURIE prefix."""


class InconsistentMapping(ValueError):
    """Raised when inconsistent prefixes are used in the keys and values of the remapping."""


class CycleDetected(ValueError):
    """Raised when the remapping induces a cycle."""


def _order_curie_remapping(
    converter: Converter, curie_remapping: Mapping[str, str]
) -> list[tuple[str, str]]:
    # Check that no keys of the remapping actually correspond to the same primary prefix
    key_counter = defaultdict(list)
    for key in curie_remapping:
        key_counter[converter.standardize_prefix(key)].append(key)
    duplicate_keys = {
        k: Counter(values) for k, values in key_counter.items() if len(values) > 1 and k is not None
    }
    if duplicate_keys:
        raise DuplicateKeys(f"Duplicate keys in remapping: {duplicate_keys}")

    # Check that it's not the case that multiple prefixes are mapping
    # to the same new prefix.
    value_counter = defaultdict(list)
    for value in curie_remapping.values():
        value_counter[converter.standardize_prefix(value)].append(value)
    duplicate_values = {
        k: Counter(values)
        for k, values in value_counter.items()
        if len(values) > 1 and k is not None
    }
    if duplicate_values:
        raise DuplicateValues(f"Duplicate values in remapping: {duplicate_values}")

    # Check that the correspondence is same for both
    correspondence_counter = defaultdict(set)
    for key, value in curie_remapping.items():
        norm_key = converter.standardize_prefix(key)
        norm_val = converter.standardize_prefix(value)
        correspondence_counter[norm_key].add(key)
        # don't penalize synonym remappings
        if norm_key != norm_val:
            correspondence_counter[norm_val].add(value)
    duplicate_correspondence = {
        k: Counter(values)
        for k, values in correspondence_counter.items()
        if len(values) > 1 and k is not None
    }
    if duplicate_correspondence:
        raise InconsistentMapping(
            f"Inconsistent usage of prefixes in keys and values: {duplicate_correspondence}"
        )

    # Given the two tests before, we don't have to worry about any clashes, and
    # we can work directly on primary prefixes
    if not set(curie_remapping).intersection(curie_remapping.values()):
        # No logic necessary, so just sort based on key to be consistent
        return sorted(curie_remapping.items())

    # assume that there are no duplicates in the values
    rv = []
    d = dict(curie_remapping)
    while d:
        no_outgoing = set(d.values()).difference(d)
        if not no_outgoing:
            raise CycleDetected("cycle detected in remapping")
        edges = sorted((k, v) for k, v in d.items() if v in no_outgoing)
        rv.extend(edges)
        d = {k: v for k, v in d.items() if v not in no_outgoing}
    return rv
