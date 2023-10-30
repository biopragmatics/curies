"""Report."""

import dataclasses
import enum
import random
import typing
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Dict, Mapping, Optional, Tuple

from .api import Converter

if TYPE_CHECKING:
    import pandas

__all__ = [
    "Report",
]


def _list(correct: typing.Sequence[str]) -> str:
    if len(correct) == 1:
        return f"`{correct[0]}`"
    if len(correct) == 2:
        return f"`{correct[0]}` or `{correct[1]}`"
    x = ", ".join(f"`{v}`" for v in correct[:-1])
    return f"{x}, or `{correct[-1]}`"


class Suggestion(enum.Enum):
    """"""

    x1 = "means data is encoded using URNs, which isn't explicitly handled by this package."
    x2 = "entries are not CURIEs, try and compressing your data first."
    x3 = "is not a valid CURIE"
    x4 = "has a double prefix annotation"
    x5 = "is a case/punctuation variant"
    x6 = "is an incorrect way of encoding a URI"
    x7 = (
        f"appears in Bioregistry under. Consider chaining your converter with the Bioregistry using "
        "[`curies.chain()`](https://curies.readthedocs.io/en/latest/api/curies.chain.html)."
    )
    xx = (
        "can either be added to the converter if it is local to the project, "
        "or if it is globally useful, contributed to the Bioregistry"
    )


@dataclasses.dataclass
class Report:
    """A report on CURIEs standardization."""

    converter: "Converter"
    column: str | int
    nones: int
    stayed: int
    updated: int
    failures: Mapping[str, typing.Counter[str]] = dataclasses.field(repr=False)

    def count_prefixes(self) -> typing.Counter[str]:
        """Count the frequency of each failing prefix."""
        return Counter({prefix: len(counter) for prefix, counter in self.failures.items()})

    def get_df(self) -> "pandas.DataFrame":
        """Summarize standardization issues in a dataframe."""
        import pandas as pd

        rows = [
            (
                prefix,
                sum(counter.values()),
                ", ".join(sorted(set(random.choices(list(counter), k=5)))),  # noqa:S311
            )
            for prefix, counter in sorted(self.failures.items(), key=lambda p: p[0].casefold())
        ]
        return pd.DataFrame(rows, columns=["prefix", "count", "examples"])

    def get_suggestions(self) -> Dict[str, Tuple[Suggestion, Optional[str]]]:
        """Get a mapping from missing prefix to suggestion text."""
        try:
            import bioregistry
        except ImportError:
            bioregistry = None

        norm_to_prefix = defaultdict(set)

        def _norm(s: str) -> str:
            for x in "_.- ":
                s = s.replace(x, "")
            return s.casefold()

        for record in self.converter.records:
            for p in record._all_prefixes:
                norm_to_prefix[_norm(p)].add(p)

        rv: dict[str, tuple[Suggestion, str | None]] = {}
        for prefix, c in self.failures.items():
            if prefix in {"url", "uri", "iri"}:
                rv[prefix] = Suggestion.x6, None
                continue
            if prefix in {"urn"}:
                rv[prefix] = Suggestion.x1, None
                continue
            if prefix in {"http", "https", "ftp"}:
                rv[prefix] = Suggestion.x2, None
                continue
            if len(c) == 1:
                first = list(c)[0]
                if first == prefix:
                    rv[prefix] = Suggestion.x3, None
                    continue
                elif first.lower() == f"{prefix.lower()}:{prefix.lower()}":
                    rv[prefix] = Suggestion.x4, prefix.lower()
                    continue
            correct = sorted(norm_to_prefix.get(_norm(prefix), []))
            if correct:
                rv[prefix] = Suggestion.x5, _list(correct)
                continue

            if bioregistry is not None:
                norm_prefix = bioregistry.normalize_prefix(prefix)
                if norm_prefix:
                    rv[prefix] = Suggestion.x7, norm_prefix
                    continue

            # TODO check for bananas?
            rv[prefix] = Suggestion.xx, None
        return rv

    def get_markdown(self) -> str:
        """Get markdown text."""
        try:
            import bioregistry
        except ImportError:
            bioregistry = None

        failures = sum(len(c) for c in self.failures.values())
        total = self.nones + self.stayed + self.updated + failures
        df = self.get_df()

        # TODO write # CURIEs, # unique CURIEs, and # unique prefixes
        text = "## Summary\n\n"
        if 0 == len(df.index):
            if not self.stayed:
                return (
                    f"Standardization was successfully applied to all "
                    f"{self.updated:,} CURIEs in column `{self.column}`."
                )
            return (
                f"Standardization was not necessary for {self.stayed:,} ({self.stayed/total:.1%}) CURIEs "
                f"and resulted in updates for {self.updated:,} ({self.updated/total:.1%}) CURIEs "
                f"in column `{self.column}`"
            )

        if bioregistry is None:
            text += "\nInstall the Bioregistry with `pip install bioregistry` for more detailed suggestions\n\n"
        text += (
            f"Standardization was not necessary for {self.stayed:,} ({self.stayed/total:.1%}), "
            f"resulted in {self.updated:,} updates ({self.updated/total:.1%}), and {failures:,} failures "
            f"({failures/total:.1%})  in column `{self.column}`. Here's a breakdown of the prefixes that "
            f"weren't possible to standardize:\n\n"
        )
        text += df.to_markdown(index=False)

        suggestions = self.get_suggestions()
        if suggestions:
            text += "\n\n## Suggestions\n\n"
            for prefix, (suggestion, extra) in suggestions.items():
                text += f"- {prefix} {suggestion}"
                if extra:
                    text += f" - {extra}"
                text += "\n"
        return text

    def _repr_markdown_(self) -> str:
        return self.get_markdown()
