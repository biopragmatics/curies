"""Reconciliation."""

from collections import Counter
from typing import Collection, Dict, List, Mapping, Optional, Tuple

from .api import Converter, Record

__all__ = [
    "remap_curie_prefixes",
    "remap_uri_prefixes",
    "rewire",
]


class TransitiveError(NotImplementedError):
    """An error when transitive mappings appear."""

    def __init__(self, intersection: Collection[str]) -> None:
        """Initialize the exception.

        :param intersection: The strings that appeared both as keys and values
            in a remapping dictionary (either for CURIEs or URIs)
        """
        self.intersection = intersection

    def __str__(self) -> str:
        return (
            f"Transitive mapping has not been implemented. This is being thrown because "
            f"the following appear in both the keys and values of the remapping: {self.intersection}."
            "\n\nSee discussion at https://github.com/cthoyt/curies/issues/75."
        )


def _get(records: Dict[str, Record], query: str) -> Optional[Record]:
    if query in records:
        return records.pop(query)
    for prefix, record in list(records.items()):
        if query in record.prefix_synonyms:
            return records.pop(prefix)
    return None


def _find(records: Mapping[str, Record], query: str) -> Optional[Record]:
    if query in records:
        return records[query]
    for record in records.values():
        if query in record.prefix_synonyms:
            return record
    return None


def remap_curie_prefixes(converter: Converter, remapping: Mapping[str, str]) -> Converter:
    """Apply CURIE prefix remappings.

    :param converter: A converter
    :param remapping: A mapping from CURIE prefixes to new CURIE prefixes.
        Old CURIE prefixes become synonyms in the records (i.e., they aren't forgotten).
    :returns: An upgraded converter
    """
    ordering = _order_mappings(remapping)
    intersection = set(remapping).intersection(remapping.values())
    records = {r.prefix: r for r in converter.records}
    modified_records = []
    for old, new_prefix in ordering:
        record = _get(records, old)
        new_record = _find(records, new_prefix)
        if record is None:
            continue  # nothing to upgrade
        elif new_record is not None and record != new_record:
            pass  # would create a clash, don't do anything
        elif old in intersection:
            # TODO handle when synonym from old appears in intersection
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
    :param remapping: A mapping from URI prefixes to new URI prefixes.
        Old URI prefixes become synonyms in the records (i.e., they aren't forgotten)
    :returns: An upgraded converter
    :raises TransitiveError: If there are any strings that appear in both
        the key and values of the remapping
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
    :param rewiring: A mapping from CURIE prefixes to new URI prefixes.
        If CURIE prefixes are not already in the converter, new records are created.
        If new URI prefixes clash with any existing ones, they are not added.
    :returns: An upgraded converter
    """
    records = []
    for record in converter.records:
        new_uri_prefix = _get_curie_preferred_or_synonym(record, rewiring)
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

    # potential future functionality: add missing records
    # for prefix, new_uri_prefix in rewiring.items():
    #     if prefix not in converter.synonym_to_prefix:
    #         records.append(Record(prefix=prefix, uri_prefix=new_uri_prefix))

    return Converter(records)


def _get_curie_preferred_or_synonym(record: Record, upgrades: Mapping[str, str]) -> Optional[str]:
    if record.prefix in upgrades:
        return upgrades[record.prefix]
    for s in record.prefix_synonyms:
        if s in upgrades:
            return upgrades[s]
    return None


def _get_uri_preferred_or_synonym(record: Record, upgrades: Mapping[str, str]) -> Optional[str]:
    if record.uri_prefix in upgrades:
        return upgrades[record.uri_prefix]
    for s in record.uri_prefix_synonyms:
        if s in upgrades:
            return upgrades[s]
    return None


def _order_mappings(remapping: Mapping[str, str]) -> List[Tuple[str, str]]:
    # Check that it's not the case that multiple prefixes are mapping
    # to the same new prefix.
    counter = Counter(remapping.values())
    duplicates = {v for v, c in counter.items() if c > 1}
    if duplicates:
        raise ValueError(f"Duplicate values in remapping: {duplicates}")

    if not set(remapping).intersection(remapping.values()):
        # No logic necessary, so just sort based on key to be consistent
        return sorted(remapping.items())

    # Check that there are no pairs k,v such that v:k is in the dict
    # sss = {frozenset([k, v]) for k, v in remapping.items() if v in remapping and remapping[v] == k}
    # if sss:
    #     raise ValueError(f"found 2-cycles: {sss}")

    # assume that there are no duplicates in the values
    rv = []
    d = dict(remapping)
    while d:
        no_outgoing = set(d.values()).difference(d)
        if not no_outgoing:
            raise ValueError("cycle detected in remapping")
        edges = sorted((k, v) for k, v in d.items() if v in no_outgoing)
        rv.extend(edges)
        d = {k: v for k, v in d.items() if v not in no_outgoing}
    return rv
