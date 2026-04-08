"""Filter functions for triples."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .model import TriplePredicate, TripleType

__all__ = [
    "exclude_object_prefixes",
    "exclude_prefixes",
    "exclude_subject_prefixes",
    "keep_object_prefixes",
    "keep_prefixes",
    "keep_subject_prefixes",
]

logger = logging.getLogger(__name__)


def _cleanup_prefixes(prefixes: str | Iterable[str]) -> set[str]:
    if isinstance(prefixes, str):
        return {prefixes}
    return set(prefixes)


def _filter(
    func: TriplePredicate[TripleType], triples: Iterable[TripleType], progress: bool = False
) -> Iterable[TripleType]:
    if progress:
        try:
            from tqdm import tqdm
        except ImportError:
            logger.warning("tqdm is not installed, can't use progress bar for %s", func)
        else:
            triples = tqdm(triples, unit="triples", unit_scale=True)
    return filter(func, triples)


def keep_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Keep triples whose subjects' and objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects' and objects'
        prefixes are in the given prefixes

    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match, c2)
    >>> m2 = Triple.from_curies(c2, exact_match, c3)
    >>> m3 = Triple.from_curies(c1, exact_match, c3)
    >>> assert list(keep_prefixes([m1, m2, m3], {"DOID", "mesh"})) == [m1]
    """
    return _filter(_keep_prefixes_filter(prefixes), triples, progress=progress)


def _keep_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    prefixes = _cleanup_prefixes(prefixes)

    def _func(triple: TripleType) -> bool:
        return triple.subject.prefix in prefixes and triple.object.prefix in prefixes

    return _func


def keep_subject_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = True
) -> Iterable[TripleType]:
    """Keep triples whose subjects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects'
        prefixes are in the given prefixes

    >>> from curies import Reference, Triple
     >>> from curies.vocabulary import exact_match
     >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
     >>> m1 = Triple.from_curies(c1, exact_match, c2)
     >>> m2 = Triple.from_curies(c2, exact_match, c3)
     >>> m3 = Triple.from_curies(c1, exact_match, c3)
     >>> assert list(keep_subject_prefixes([m1, m2, m3], {"DOID"})) == [m1, m2]
    """
    return _filter(_keep_subject_prefixes_filter(prefixes), triples, progress=progress)


def _keep_subject_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    prefixes = _cleanup_prefixes(prefixes)

    def _func(triple: TripleType) -> bool:
        return triple.subject.prefix in prefixes

    return _func


def keep_object_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = True
) -> Iterable[TripleType]:
    """Keep triples whose objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose objects'
        prefixes are in the given prefixes


    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match, c2)
    >>> m2 = Triple.from_curies(c2, exact_match, c3)
    >>> m3 = Triple.from_curies(c1, exact_match, c3)
    >>> assert list(keep_object_prefixes([m1, m2, m3], {"umls"})) == [m2, m3]
    """
    return _filter(_keep_object_prefixes_filter(prefixes), triples, progress=progress)


def _keep_object_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    prefixes = _cleanup_prefixes(prefixes)

    def _func(triple: TripleType) -> bool:
        return triple.object.prefix in prefixes

    return _func


def exclude_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = False
) -> Iterable[TripleType]:
    """Exclude triples whose subjects' and objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects' and objects'
        prefixes are not in the given prefixes

    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match, c2)
    >>> m2 = Triple.from_curies(c2, exact_match, c3)
    >>> m3 = Triple.from_curies(c1, exact_match, c3)
    >>> assert list(exclude_prefixes([m1, m2, m3], {"umls"})) == [m1]
    >>> assert list(exclude_prefixes([m1, m2, m3], {"DOID"})) == [m2]
    >>> assert list(exclude_prefixes([m1, m2, m3], {"mesh"})) == [m3]
    """
    return _filter(_exclude_prefixes_filter(prefixes), triples, progress=progress)


def _exclude_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    prefixes = _cleanup_prefixes(prefixes)

    def _func(triple: TripleType) -> bool:
        return triple.subject.prefix not in prefixes and triple.object.prefix not in prefixes

    return _func


def exclude_subject_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = True
) -> Iterable[TripleType]:
    """Exclude triples whose subjects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose subjects'
        prefixes are not in the given prefixes

    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match, c2)
    >>> m2 = Triple.from_curies(c2, exact_match, c3)
    >>> m3 = Triple.from_curies(c1, exact_match, c3)
    >>> assert list(exclude_subject_prefixes([m1, m2, m3], {"DOID"})) == [m2]
    >>> assert list(exclude_subject_prefixes([m1, m2, m3], {"umls"})) == [m1, m2, m3]
    >>> assert list(exclude_subject_prefixes([m1, m2, m3], {"mesh"})) == [m1, m3]
    """
    return _filter(_exclude_subject_prefixes_filter(prefixes), triples, progress=progress)


def _exclude_subject_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    prefixes = _cleanup_prefixes(prefixes)

    def _func(triple: TripleType) -> bool:
        return triple.subject.prefix not in prefixes

    return _func


def exclude_object_prefixes(
    triples: Iterable[TripleType], prefixes: str | Iterable[str], *, progress: bool = True
) -> Iterable[TripleType]:
    """Exclude triples whose objects' prefixes are in the given prefixes.

    :param triples: An iterable of triples
    :param prefixes: A set of prefixes to use for filtering the triples
    :param progress: Should a progress bar be shown?

    :returns: A sub-iterable of triples whose objects'
        prefixes are not in the given prefixes


    >>> from curies import Reference, Triple
    >>> from curies.vocabulary import exact_match
    >>> c1, c2, c3 = "DOID:0050577", "mesh:C562966", "umls:C4551571"
    >>> m1 = Triple.from_curies(c1, exact_match, c2)
    >>> m2 = Triple.from_curies(c2, exact_match, c3)
    >>> m3 = Triple.from_curies(c1, exact_match, c3)
    >>> assert list(exclude_object_prefixes([m1, m2, m3], {"umls"})) == [m1]
    >>> assert list(exclude_object_prefixes([m1, m2, m3], {"mesh"})) == [m2, m3]
    >>> assert list(exclude_object_prefixes([m1, m2, m3], {"DOID"})) == [m1, m2, m3]
    """
    return _filter(_exclude_object_prefixes_filter(prefixes), triples, progress=progress)


def _exclude_object_prefixes_filter(prefixes: str | Iterable[str]) -> TriplePredicate[TripleType]:
    prefixes = _cleanup_prefixes(prefixes)

    def _func(triple: TripleType) -> bool:
        return triple.object.prefix not in prefixes

    return _func
