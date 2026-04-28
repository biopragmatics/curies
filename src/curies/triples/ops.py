"""Operations on triples."""

from collections import defaultdict
from collections.abc import Iterable
from typing import TypeAlias

from .model import TripleType
from .. import Reference

__all__ = [
    "SubjectObjectIndex",
    "get_many_to_many",
    "get_simple_indexes",
    "get_subject_object_indexes",
]

#: A multi-leveled nested dictionary that represents many-to-many mappings.
#: The first key is subject/object pairs, the second key is either a subject identifier or object identifier,
#: the last key is the opposite object or subject identifier, and the values are a list of mappings.
#:
#: This data structure can be used to index either forward or backwards mappings,
#: as done inside :func:`get_many_to_many`
SubjectObjectIndex: TypeAlias = dict[tuple[str, str], dict[str, dict[str, list[TripleType]]]]

_DD = defaultdict[tuple[str, str], defaultdict[str, defaultdict[str, list[TripleType]]]]


def _downgrade_defaultdict(dd: _DD[TripleType]) -> SubjectObjectIndex[TripleType]:
    return {k1: {k2: dict(v2) for k2, v2 in v1.items()} for k1, v1 in dd.items()}


def get_subject_object_indexes(
    triples: Iterable[TripleType],
) -> tuple[SubjectObjectIndex[TripleType], SubjectObjectIndex[TripleType]]:
    """Get a forward and backwards subject/object index.

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
        backward[triple.object.prefix, triple.subject.prefix][triple.object.identifier][
            triple.subject.identifier
        ].append(triple)
    return _downgrade_defaultdict(forward), _downgrade_defaultdict(backward)


SimpleIndex = dict[Reference, set[Reference]]


def get_simple_indexes(triples: Iterable[TripleType]) -> tuple[SimpleIndex, SimpleIndex]:
    """Get simple entity indexes."""
    forward = defaultdict(set)
    backward = defaultdict(set)
    for triple in triples:
        forward[triple.subject].add(triple.object)
        backward[triple.object].add(triple.subject)
    return dict(forward), dict(backward)


def get_one_to_many(
    forward_index: SubjectObjectIndex[TripleType],
) -> dict[tuple[str, str], dict[str, set[str]]]:
    return {
        pair: xx
        for pair, inner in forward_index.items()
        if (xx := {k: set(v) for k, v in inner.items() if len(v) > 1})
    }


def get_many_to_one(forward: SubjectObjectIndex[TripleType]) -> dict[str, set[str]]:
    raise NotImplementedError


def get_many_to_many(triples: Iterable[TripleType]) -> set[Reference]:
    """Get many to many triples."""
    raise NotImplementedError
