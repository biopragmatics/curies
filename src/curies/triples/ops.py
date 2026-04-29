"""Operations on triples."""

from collections import defaultdict
from collections.abc import Iterable
from typing import TypeAlias

from .filters import exclude_triples
from .model import TripleType
from .. import Reference

__all__ = [
    "PrefixPairStratifiedIndex",
    "exclude_prefix_stratified_many_to_many",
    "exclude_triples",
    "get_prefix_pair_stratified_indexes",
    "get_prefix_stratified_many_to_many",
    "get_reference_indexes",
]

#: A doubly-nested adjacency dictionary whose first
#: keys are subject/object local unique identifier,
#: second level is the opposite side local unique
#: identifier, and values are the list of triples
AdjacencyDict = dict[str, dict[str, list[TripleType]]]

#: A pair of prefixes
PrefixPair: TypeAlias = tuple[str, str]

#: A multi-leveled nested dictionary that represents many-to-many mappings.
#: The first key is subject/object pairs, the second key is either a subject identifier or object identifier,
#: the last key is the opposite object or subject identifier, and the values are a list of mappings.
#:
#: This data structure can be used to index either forward or backwards mappings,
#: as done inside :func:`get_many_to_many`
PrefixPairStratifiedIndex: TypeAlias = dict[PrefixPair, AdjacencyDict[TripleType]]


def exclude_prefix_stratified_many_to_many(
    triples: Iterable[TripleType], *, progress: bool = False
) -> Iterable[TripleType]:
    """Exclude prefix pair-stratified many-to-many relationships.

    .. warning::

        This function does not consider the predicate, so if you only want to make this
        operation based on specific predicate, then pre-group your triples based on
        predicate.

    :param triples: An iterable of triples
    :param progress: Whether to show a progress bar

    :returns: An iterable of triples

        .. warning::

            This operation fully consumes the iterator since it requires two passes


    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match, subclass_of
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "DOID:225"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, subclass_of.curie, c3)
    >>> assert list(exclude_triples([m1, m2, m3], m3)) == [m1, m2]
    """
    triples = list(triples)
    exclusion = get_prefix_stratified_many_to_many(triples)
    return exclude_triples(triples, exclusion, progress=progress)


def get_prefix_stratified_many_to_many(triples: Iterable[TripleType]) -> set[TripleType]:
    """Get many-to-many relationships."""
    forward, backward = get_prefix_pair_stratified_indexes(triples)
    forward_sliced = get_one_to_many(forward)
    backwards_sliced_flipped = flip_prefix_pair_stratified_index(get_one_to_many(backward))
    rv: set[TripleType] = set()
    for prefix_pair, forward_adjacency_dict in forward_sliced.items():
        if backward_adjacency_dict := backwards_sliced_flipped.get(prefix_pair):
            rv.update(_compare(forward_adjacency_dict, backward_adjacency_dict))
    return rv


def get_prefix_pair_stratified_indexes(
    triples: Iterable[TripleType],
) -> tuple[PrefixPairStratifiedIndex[TripleType], PrefixPairStratifiedIndex[TripleType]]:
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


_DD = defaultdict[PrefixPair, defaultdict[str, defaultdict[str, list[TripleType]]]]


def _downgrade_defaultdict(dd: _DD[TripleType]) -> PrefixPairStratifiedIndex[TripleType]:
    return {k1: {k2: dict(v2) for k2, v2 in v1.items()} for k1, v1 in dd.items()}


def get_one_to_many(
    index: PrefixPairStratifiedIndex[TripleType],
) -> PrefixPairStratifiedIndex[TripleType]:
    """Filter an index to entities in each prefix pair with a one-to-many relationship."""
    rv = {}
    for pair, inner in index.items():
        filtered_inner = {k: v for k, v in inner.items() if len(v) > 1}
        if filtered_inner:
            rv[pair] = filtered_inner
    return rv


def flip_prefix_pair_stratified_index(
    index: PrefixPairStratifiedIndex[TripleType],
) -> PrefixPairStratifiedIndex[TripleType]:
    """Flip a one-to-many relationship index to a many-to-one relationship index."""
    rv = {}
    for (left, right), adjacency_dict in index.items():
        flipped_adjacency_dict: defaultdict[str, dict[str, list[TripleType]]] = defaultdict(dict)
        for left_id, inner_dict in adjacency_dict.items():
            for right_id, triples in inner_dict.items():
                flipped_adjacency_dict[right_id][left_id] = triples
        rv[right, left] = {k: v for k, v in flipped_adjacency_dict.items() if len(v) > 1}
    return rv


def _compare(
    left_adjacency_dict: AdjacencyDict[TripleType], right_adjacency_dict: AdjacencyDict[TripleType]
) -> set[TripleType]:
    rv = set()
    keys = set(left_adjacency_dict.keys()) & set(right_adjacency_dict.keys())
    for key in keys:
        inner_keys = set(left_adjacency_dict[key]) & set(right_adjacency_dict[key])
        for inner_key in inner_keys:
            rv.update(left_adjacency_dict[key][inner_key])
    return rv


#: A simple index from reference to references. This can
#: either be subject to objects, or object to subjects,
#: depending on the implementation.
ReferenceIndex = dict[Reference, set[Reference]]


def get_reference_indexes(triples: Iterable[TripleType]) -> tuple[ReferenceIndex, ReferenceIndex]:
    """Get simple entity indexes."""
    forward = defaultdict(set)
    backward = defaultdict(set)
    for triple in triples:
        forward[triple.subject].add(triple.object)
        backward[triple.object].add(triple.subject)
    return dict(forward), dict(backward)
