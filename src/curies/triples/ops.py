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
    # forward index
    f: _DD[TripleType] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    # backward index
    b: _DD[TripleType] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for t in triples:
        f[t.subject.prefix, t.object.prefix][t.subject.identifier][t.object.identifier].append(t)
        b[t.object.prefix, t.subject.prefix][t.object.identifier][t.subject.identifier].append(t)
    return _downgrade_defaultdict(f), _downgrade_defaultdict(b)


def get_one_to_many(index: SubjectObjectIndex[TripleType]) -> SubjectObjectIndex[TripleType]:
    rv = {}
    for pair, inner in index.items():
        filtered_inner = {k: v for k, v in inner.items() if len(v) > 1}
        if filtered_inner:
            rv[pair] = filtered_inner
    return rv


def flip(d: SubjectObjectIndex[TripleType]) -> SubjectObjectIndex[TripleType]:
    rv = {}
    for (left, right), inner1 in d.items():
        ddd = defaultdict(dict)
        for subject_id, inner2 in inner1.items():
            for object_id, triples in inner2.items():
                ddd[object_id][subject_id] = triples
        rv[right, left] = {k: v for k, v in ddd.items() if len(v) > 1}
    return rv


def get_many_to_many(triples: Iterable[TripleType]) -> set[TripleType]:
    """Get many to many triples."""
    forward, backward = get_subject_object_indexes(triples)
    forward_sliced = get_one_to_many(forward)
    b = flip(get_one_to_many(backward))
    rv = set()
    for pair, xx in forward_sliced.items():
        if yy := b.get(pair):
            rv.update(_compare(xx, yy))
    return rv


def _compare(xx, yy) -> set[TripleType]:
    rv = set()
    keys = set(xx.keys()) & set(yy.keys())
    for key in keys:
        inner_keys = set(xx[key]) & set(yy[key])
        for value in inner_keys:
            rv.add((key, value))
    return rv


#: A simple index from reference to references. This can
#: either be subject to objects, or object to subjects,
#: depending on the implementation.
SimpleIndex = dict[Reference, set[Reference]]


def get_simple_indexes(triples: Iterable[TripleType]) -> tuple[SimpleIndex, SimpleIndex]:
    """Get simple entity indexes."""
    forward = defaultdict(set)
    backward = defaultdict(set)
    for triple in triples:
        forward[triple.subject].add(triple.object)
        backward[triple.object].add(triple.subject)
    return dict(forward), dict(backward)
