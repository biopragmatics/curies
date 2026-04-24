"""Operations on triples."""

from collections import defaultdict
from collections.abc import Iterable

from .model import TripleType

__all__ = [
    "ManyToManyIndex",
    "get_subject_object_indexes",
]

#: A multi-leveled nested dictionary that represents many-to-many mappings.
#: The first key is subject/object pairs, the second key is either a subject identifier or object identifier,
#: the last key is the opposite object or subject identifier, and the values are a list of mappings.
#:
#: This data structure can be used to index either forward or backwards mappings,
#: as done inside :func:`get_many_to_many`
ManyToManyIndex = dict[tuple[str, str], dict[str, dict[str, list[TripleType]]]]

_DD = defaultdict[tuple[str, str], defaultdict[str, defaultdict[str, list[TripleType]]]]


def _fix_dd(dd: _DD[TripleType]) -> ManyToManyIndex[TripleType]:
    return {k1: {k2: dict(v2) for k2, v2 in v1.items()} for k1, v1 in dd.items()}


def get_subject_object_indexes(
    triples: Iterable[TripleType],
) -> tuple[ManyToManyIndex[TripleType], ManyToManyIndex[TripleType]]:
    """Get a forward and backwards many-to-many index.

    :param triples: An iterable of triples

    :returns: A pair of forward and backwards indexes, where:

        - A forward many-to-many index is a triply-nested dictionary from
          subject/predicate prefix pair to subject identifier to object identifier to
          list of triples.
        - A backward many-to-many index is a triply-nested dictionary from
          subject/predicate prefix pair to object identifier to subject identifier to
          list of triples.
    """
    forward: _DD[TripleType] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    backward: _DD[TripleType] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for triple in triples:
        forward[triple.subject.prefix, triple.object.prefix][triple.subject.identifier][
            triple.object.identifier
        ].append(triple)
        backward[triple.subject.prefix, triple.object.prefix][triple.object.identifier][
            triple.subject.identifier
        ].append(triple)
    return _fix_dd(forward), _fix_dd(backward)


def get_many_to_many(triples: Iterable[TripleType]) -> list[TripleType]:
    """Get many to many triples."""
    raise NotImplementedError
