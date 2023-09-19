"""Reconciliation."""

from typing import Collection, Mapping, Optional

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


def remap_curie_prefixes(converter: Converter, remapping: Mapping[str, str]) -> Converter:
    """Apply CURIE prefix remappings.

    :param converter: A converter
    :param remapping: A mapping from CURIE prefixes to new CURIE prefixes.
        Old CURIE prefixes become synonyms in the records (i.e., they aren't forgotten)
    :returns: An upgraded converter
    :raises TransitiveError: If there are any strings that appear in both
        the key and values of the remapping
    """
    intersection = set(remapping).intersection(remapping.values())
    if intersection:
        raise TransitiveError(intersection)

    records = []
    for record in converter.records:
        new_prefix = _get_curie_preferred_or_synonym(record, remapping)
        if new_prefix is None:
            pass  # nothing to upgrade
        elif new_prefix in converter.synonym_to_prefix and new_prefix not in record.prefix_synonyms:
            pass  # would create a clash, don't do anything
        else:
            record.prefix_synonyms = sorted(
                set(record.prefix_synonyms).union({record.prefix}).difference({new_prefix})
            )
            record.prefix = new_prefix
        records.append(record)
    return Converter(records)


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
