"""Filter functions for triples."""

from __future__ import annotations

import logging
from collections.abc import Collection, Iterable

from .model import Triple, TriplePredicate, TripleType
from ..api import Converter, Reference

__all__ = [
    "exclude_object_prefixes",
    "exclude_prefixes_both",
    "exclude_references_both",
    "exclude_same_prefixes",
    "exclude_subject_prefixes",
    "exclude_triples",
    "keep_object_prefixes",
    "keep_prefixes_both",
    "keep_prefixes_either",
    "keep_references_both",
    "keep_references_either",
    "keep_subject_prefixes",
    "keep_triples_by_hash",
]

logger = logging.getLogger(__name__)


def _filter(
    func: TriplePredicate[TripleType], triples: Iterable[TripleType], progress: bool = False
) -> Iterable[TripleType]:
    if progress:  # pragma: no cover
        try:
            from tqdm import tqdm
        except ImportError:
            logger.warning("tqdm is not installed, can't use progress bar for %s", func)
        else:
            triples = tqdm(triples, unit="triples", unit_scale=True)
    return filter(func, triples)


def keep_prefixes_both(
    triples: Iterable[TripleType], prefixes: Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Keep triples whose subjects' and objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects' and objects' prefixes are in the
        given prefixes

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, exact_match.curie, c3)
    >>> assert list(keep_prefixes_both([m1, m2, m3], {"DOID", "mesh"})) == [m1]
    """
    return _filter(_keep_prefixes_both_filter(prefixes), triples, progress=progress)


def _keep_prefixes_both_filter(prefixes: Iterable[str]) -> TriplePredicate[TripleType]:
    prefixes = set(prefixes)
    if len(prefixes) < 2:
        raise ValueError

    def _func(triple: TripleType) -> bool:
        return triple.subject.prefix in prefixes and triple.object.prefix in prefixes

    return _func


def keep_prefixes_either(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Keep triples whose subjects' and objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects' and objects' prefixes are in the
        given prefixes

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, exact_match.curie, c3)
    >>> assert list(keep_prefixes_either([m1, m2, m3], {"DOID", "mesh"})) == [m1]
    """
    return _filter(_keep_prefixes_either_filter(prefixes), triples, progress=progress)


def _keep_prefixes_either_filter(prefixes: Iterable[str]) -> TriplePredicate[TripleType]:
    if isinstance(prefixes, str):

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix == prefixes or triple.object.prefix == prefixes

    else:
        prefixes = set(prefixes)

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix in prefixes or triple.object.prefix in prefixes

    return _func


def keep_subject_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Keep triples whose subjects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects' prefixes are in the given
        prefixes

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, exact_match.curie, c3)
    >>> assert list(keep_subject_prefixes([m1, m2, m3], {"DOID"})) == [m1, m3]
    """
    return _filter(_keep_subject_prefixes_filter(prefixes), triples, progress=progress)


def _keep_subject_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    if isinstance(prefixes, str):

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix == prefixes

    else:
        prefixes = set(prefixes)

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix in prefixes

    return _func


def keep_object_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Keep triples whose objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose objects' prefixes are in the given
        prefixes

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, exact_match.curie, c3)
    >>> assert list(keep_object_prefixes([m1, m2, m3], {"umls"})) == [m2, m3]
    """
    return _filter(_keep_object_prefixes_filter(prefixes), triples, progress=progress)


def _keep_object_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    if isinstance(prefixes, str):

        def _func(triple: TripleType) -> bool:
            return triple.object.prefix == prefixes
    else:
        prefixes = set(prefixes)

        def _func(triple: TripleType) -> bool:
            return triple.object.prefix in prefixes

    return _func


def exclude_prefixes_both(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Exclude triples whose subjects' and objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects' and objects' prefixes are not in
        the given prefixes

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, exact_match.curie, c3)
    >>> assert list(exclude_prefixes_both([m1, m2, m3], {"umls"})) == [m1]
    >>> assert list(exclude_prefixes_both([m1, m2, m3], {"DOID"})) == [m2]
    >>> assert list(exclude_prefixes_both([m1, m2, m3], {"mesh"})) == [m3]
    """
    return _filter(_exclude_prefixes_filter(prefixes), triples, progress=progress)


def _exclude_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    if isinstance(prefixes, str):

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix != prefixes and triple.object.prefix != prefixes

    else:
        prefixes = set(prefixes)

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix not in prefixes and triple.object.prefix not in prefixes

    return _func


def exclude_subject_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Exclude triples whose subjects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects' prefixes are not in the given
        prefixes

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, exact_match.curie, c3)
    >>> assert list(exclude_subject_prefixes([m1, m2, m3], {"DOID"})) == [m2]
    >>> assert list(exclude_subject_prefixes([m1, m2, m3], {"umls"})) == [m1, m2, m3]
    >>> assert list(exclude_subject_prefixes([m1, m2, m3], {"mesh"})) == [m1, m3]
    """
    return _filter(_exclude_subject_prefixes_filter(prefixes), triples, progress=progress)


def _exclude_subject_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    if isinstance(prefixes, str):

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix != prefixes

    else:
        prefixes = set(prefixes)

        def _func(triple: TripleType) -> bool:
            return triple.subject.prefix not in prefixes

    return _func


def exclude_object_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Exclude triples whose objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose objects' prefixes are not in the given
        prefixes

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, exact_match.curie, c3)
    >>> assert list(exclude_object_prefixes([m1, m2, m3], {"umls"})) == [m1]
    >>> assert list(exclude_object_prefixes([m1, m2, m3], {"mesh"})) == [m2, m3]
    >>> assert list(exclude_object_prefixes([m1, m2, m3], {"DOID"})) == [m1, m2, m3]
    """
    return _filter(_exclude_object_prefixes_filter(prefixes), triples, progress=progress)


def _exclude_object_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    if isinstance(prefixes, str):

        def _func(triple: TripleType) -> bool:
            return triple.object.prefix != prefixes

    else:
        prefixes = set(prefixes)

        def _func(triple: TripleType) -> bool:
            return triple.object.prefix not in prefixes

    return _func


def exclude_same_prefixes(
    triples: Iterable[TripleType], *, progress: bool = False
) -> Iterable[TripleType]:
    """Exclude triples whose subject and object prefixes are the same.

    :param triples: An iterable of triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subject and object prefixes are not the
        same.

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match, subclass_of
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "DOID:225"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, subclass_of.curie, c3)
    >>> assert list(exclude_same_prefixes([m1, m2, m3])) == [m1, m2]
    """
    return _filter(_same_prefix_filter, triples, progress=progress)


def _same_prefix_filter(triple: TripleType) -> bool:
    return triple.subject.prefix != triple.object.prefix


def keep_triples_by_hash(
    triples: Iterable[TripleType],
    converter: Converter,
    triple_hashes: str | Iterable[str],
    *,
    progress: bool = False,
) -> Iterable[TripleType]:
    """Keep triples whose triple hash (under the given converter) is in the given collection.

    :param triples: An iterable of triples
    :param converter: A converter
    :param triple_hashes: A hash or hashs to check triples for
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose triple hash under the given constructor
        appears in the given collection

    >>> from curies import Triple, Converter
    >>> from curies.vocabulary import exact_match, subclass_of
    >>> converter = Converter.from_prefix_map(
    ...     {
    ...         "DOID": "http://purl.obolibrary.org/obo/DOID_",
    ...         "skos": "http://www.w3.org/2004/02/skos/core#",
    ...         "mesh": "http://id.nlm.nih.gov/mesh/",
    ...         "umls": "https://uts.nlm.nih.gov/uts/umls/concept/",
    ...     }
    ... )
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "DOID:225"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, subclass_of.curie, c3)
    >>> m1_hash = "081f943d3791dae3a85f8eb9190fee3fbdc47ba269a374e4a0a28a2b0b982625"
    >>> assert list(keep_triples_by_hash([m1, m2, m3], converter, m1_hash)) == [m1]
    """
    return _filter(_triple_has_hash(converter, triple_hashes), triples, progress=progress)


def _triple_has_hash(
    converter: Converter, triple_hashes: str | Iterable[str]
) -> TriplePredicate[TripleType]:
    if isinstance(triple_hashes, str):

        def _func(triple: TripleType) -> bool:
            return converter.hash_triple(triple) == triple_hashes
    else:
        triple_hashes = set(triple_hashes)

        def _func(triple: TripleType) -> bool:
            return converter.hash_triple(triple) in triple_hashes

    return _func


def exclude_triples(
    triples: Iterable[TripleType],
    exclusion: TripleType | Collection[TripleType],
    *,
    progress: bool = False,
) -> Iterable[TripleType]:
    """Exclude triples in the given set.

    :param triples: An iterable of triples
    :param exclusion: A triple or collection of triples to exclude
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subject and object prefixes are not the
        same.

    >>> from curies import Triple
    >>> from curies.vocabulary import exact_match, subclass_of
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "DOID:225"
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, subclass_of.curie, c3)
    >>> assert list(exclude_triples([m1, m2, m3], m3)) == [m1, m2]
    """
    return _filter(_exclude_triples(exclusion), triples, progress=progress)


def _exclude_triples(
    exclusion_triples: TripleType | Iterable[TripleType],
) -> TriplePredicate[TripleType]:
    if isinstance(exclusion_triples, Triple):
        exclusion_triples = {exclusion_triples}
    else:
        exclusion_triples = set(exclusion_triples)

    def _func(triple: TripleType) -> bool:
        return triple not in exclusion_triples

    return _func


def keep_references_either(
    triples: Iterable[TripleType],
    references: Reference | Collection[Reference],
    *,
    progress: bool = False,
) -> Iterable[TripleType]:
    """Keep triples whose subject and object appear in the given references.

    :param triples: An iterable of triples
    :param references: A collection of references
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subject and object appear in the given
        references.

    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match, subclass_of
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "DOID:225"
    >>> r1, r2, r3 = (Reference.from_curie(c) for c in (c1, c2, c3))
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, subclass_of.curie, c3)
    >>> assert list(keep_references_either([m1, m2, m3], [r2, r1])) == [m1]
    """
    return _filter(_include_references_either(references), triples, progress=progress)


def _include_references_either(
    references: Reference | Collection[Reference],
) -> TriplePredicate[TripleType]:
    if isinstance(references, Reference):

        def _func(triple: TripleType) -> bool:
            return triple.subject == references or triple.object == references

    else:
        references = set(references)

        def _func(triple: TripleType) -> bool:
            return triple.subject in references or triple.object in references

    return _func


def keep_references_both(
    triples: Iterable[TripleType], references: Collection[Reference], *, progress: bool = False
) -> Iterable[TripleType]:
    """Keep triples whose subject and object appear in the given references.

    :param triples: An iterable of triples
    :param references: A collection of references
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subject and object appear in the given
        references.

    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match, subclass_of
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "DOID:225"
    >>> r1, r2, r3 = (Reference.from_curie(c) for c in (c1, c2, c3))
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, subclass_of.curie, c3)
    >>> assert list(keep_references_both([m1, m2, m3], [r2, r1])) == [m1]
    """
    return _filter(_include_references_both(references), triples, progress=progress)


def _include_references_both(references: Collection[Reference]) -> TriplePredicate[TripleType]:
    references = set(references)
    if len(references) < 2:
        raise ValueError("two or more references are required")

    def _func(triple: TripleType) -> bool:
        return triple.subject in references and triple.object in references

    return _func


def exclude_references_both(
    triples: Iterable[TripleType],
    references: Reference | Collection[Reference],
    *,
    progress: bool = False,
) -> Iterable[TripleType]:
    """Exclude triples whose subject and object appear in the given references.

    :param triples: An iterable of triples
    :param references: A collection of references
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subject and object don't appear in the
        given references.

    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match, subclass_of
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "DOID:225"
    >>> r1, r2, r3 = (Reference.from_curie(c) for c in (c1, c2, c3))
    >>> m1 = Triple.from_curies(c1, exact_match.curie, c2)
    >>> m2 = Triple.from_curies(c2, exact_match.curie, c3)
    >>> m3 = Triple.from_curies(c1, subclass_of.curie, c3)
    >>> assert list(exclude_references_both([m1, m2, m3], [r1])) == [m2]
    >>> assert list(exclude_references_both([m1, m2, m3], [r2])) == [m3]
    >>> assert list(exclude_references_both([m1, m2, m3], [r3])) == [m1]
    """
    return _filter(_exclude_references(references), triples, progress=progress)


def _exclude_references(
    references: Reference | Collection[Reference],
) -> TriplePredicate[TripleType]:
    if isinstance(references, Reference):
        references = {references}
    else:
        references = set(references)

    def _func(triple: TripleType) -> bool:
        return triple.subject not in references and triple.object not in references

    return _func
