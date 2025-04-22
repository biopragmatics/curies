"""Reusable configuration."""

import json
from pathlib import Path
from typing import Any, Literal, TypeVar, overload

from pydantic import BaseModel, Field
from typing_extensions import Self

from .api import Converter, Reference, ReferenceTuple

__all__ = [
    "Blacklist",
    "BlacklistError",
    "PreprocessingConverter",
    "Rewrites",
    "Rules",
]

X = TypeVar("X", bound=Reference)


class Blacklist(BaseModel):
    """A model for prefix and full blacklists."""

    full: list[str] = Field(default_factory=list)
    resource_full: dict[str, list[str]] = Field(default_factory=dict)
    prefix: list[str] = Field(default_factory=list)
    resource_prefix: dict[str, list[str]] = Field(default_factory=dict)
    suffix: list[str] = Field(default_factory=list)

    def _sort(self) -> None:
        self.full.sort()
        self.prefix.sort()
        self.suffix.sort()
        for v in self.resource_full.values():
            v.sort()
        for v in self.resource_prefix.values():
            v.sort()

    def str_has_blacklisted_prefix(
        self, str_or_curie_or_uri: str, *, ontology_prefix: str | None = None
    ) -> bool:
        """Check if the CURIE string has a blacklisted prefix."""
        if ontology_prefix:
            prefixes: list[str] = self.resource_prefix.get(ontology_prefix, [])
            if prefixes and any(str_or_curie_or_uri.startswith(prefix) for prefix in prefixes):
                return True
        return any(str_or_curie_or_uri.startswith(prefix) for prefix in self.prefix)

    def str_has_blacklisted_suffix(self, str_or_curie_or_uri: str) -> bool:
        """Check if the CURIE string has a blacklisted suffix."""
        return any(str_or_curie_or_uri.endswith(suffix) for suffix in self.suffix)

    def str_is_blacklisted_full(
        self, str_or_curie_or_uri: str, *, ontology_prefix: str | None = None
    ) -> bool:
        """Check if the full CURIE string is blacklisted."""
        if ontology_prefix and str_or_curie_or_uri in self.resource_full.get(
            ontology_prefix, set()
        ):
            return True
        return str_or_curie_or_uri in self.full

    def str_is_blacklisted(
        self, str_or_curie_or_uri: str, *, ontology_prefix: str | None = None
    ) -> bool:
        """Check if the full CURIE string is blacklisted."""
        return (
            self.str_has_blacklisted_prefix(str_or_curie_or_uri, ontology_prefix=ontology_prefix)
            or self.str_has_blacklisted_suffix(str_or_curie_or_uri)
            or self.str_is_blacklisted_full(str_or_curie_or_uri, ontology_prefix=ontology_prefix)
        )


class Rewrites(BaseModel):
    """A model for prefix and full rewrites."""

    full: dict[str, str] = Field(
        default_factory=dict, description="Global remappings for an entire string"
    )
    resource_full: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Resource-keyed remappings for an entire string"
    )
    prefix: dict[str, str] = Field(
        default_factory=dict, description="Global remappings of just the prefix"
    )
    resource_prefix: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Resource-keyed remappings for just a prefix"
    )

    def remap_full(
        self, str_or_curie_or_uri: str, cls: type[X], *, ontology_prefix: str | None = None
    ) -> X | None:
        """Remap the string if possible otherwise return it."""
        if ontology_prefix:
            resource_rewrites: dict[str, str] = self.resource_full.get(ontology_prefix, {})
            if resource_rewrites and str_or_curie_or_uri in resource_rewrites:
                return cls.from_curie(resource_rewrites[str_or_curie_or_uri])

        if str_or_curie_or_uri in self.full:
            return cls.from_curie(self.full[str_or_curie_or_uri])

        return None

    def remap_prefix(self, str_or_curie_or_uri: str, ontology_prefix: str | None = None) -> str:
        """Remap a prefix."""
        if ontology_prefix is not None:
            for old_prefix, new_prefix in self.resource_prefix.get(ontology_prefix, {}).items():
                if str_or_curie_or_uri.startswith(old_prefix):
                    return new_prefix + str_or_curie_or_uri[len(old_prefix) :]
        for old_prefix, new_prefix in self.prefix.items():
            if str_or_curie_or_uri.startswith(old_prefix):
                return new_prefix + str_or_curie_or_uri[len(old_prefix) :]
        return str_or_curie_or_uri


class Rules(BaseModel):
    """A model for blacklists and rewrites."""

    blacklists: Blacklist
    rewrites: Rewrites

    @classmethod
    def lint_file(cls, path: str | Path) -> None:
        """Lint a file."""
        path = Path(path).expanduser().resolve()
        rules = cls.model_validate_json(path.read_text())
        rules.blacklists._sort()
        path.write_text(json.dumps(rules.model_dump(), sort_keys=True, indent=2))

    def str_is_blacklisted(
        self, str_or_curie_or_uri: str, *, ontology_prefix: str | None = None
    ) -> bool:
        """Check if the CURIE string is blacklisted."""
        return self.blacklists.str_is_blacklisted(
            str_or_curie_or_uri, ontology_prefix=ontology_prefix
        )

    def remap_full(
        self, str_or_curie_or_uri: str, cls: type[X], *, ontology_prefix: str | None = None
    ) -> X | None:
        """Remap the string if possible otherwise return it."""
        return self.rewrites.remap_full(
            str_or_curie_or_uri, cls=cls, ontology_prefix=ontology_prefix
        )

    def remap_prefix(self, str_or_curie_or_uri: str, ontology_prefix: str | None = None) -> str:
        """Remap a prefix."""
        return self.rewrites.remap_prefix(str_or_curie_or_uri, ontology_prefix=ontology_prefix)


def _load_rules(rules: str | Path | Rules) -> Rules:
    if isinstance(rules, str | Path):
        rules = Path(rules).expanduser().resolve()
        rules = Rules.model_validate_json(rules.read_text())
    return rules


class BlacklistError(ValueError):
    """An error for blacklist."""


class PreprocessingConverter(Converter):
    """A converter with pre-processing rules."""

    def __init__(self, *args: Any, rules: Rules | str | Path, **kwargs: Any) -> None:
        """Instantiate a converter with a ruleset for pre-processing.

        :param args: Positional arguments passed to :func:`Converter.__init__`
        :param rules: A set of rules
        :param kwargs: Keyword arguments passed to :func:`Converter.__init__`
        """
        super().__init__(*args, **kwargs)
        self.rules = _load_rules(rules)
        self._cls = Reference

    @classmethod
    def from_converter(cls, converter: Converter, rules: Rules | str | Path) -> Self:
        """Wrap a converter with a ruleset."""
        return cls(records=converter.records, rules=rules)

    @overload
    def parse(
        self, uri_or_curie: str, *, strict: Literal[True] = True, ontology_prefix: str | None = ...
    ) -> ReferenceTuple: ...

    @overload
    def parse(
        self,
        uri_or_curie: str,
        *,
        strict: Literal[False] = False,
        ontology_prefix: str | None = ...,
    ) -> ReferenceTuple | None: ...

    def parse(
        self, str_or_uri_or_curie: str, *, strict: bool = False, ontology_prefix: str | None = None
    ) -> ReferenceTuple | None:
        """Parse a string, CURIE, or URI."""
        if r1 := self.rules.remap_full(
            str_or_uri_or_curie, cls=self._cls, ontology_prefix=ontology_prefix
        ):
            return r1.pair

        # Remap node's prefix (if necessary)
        str_or_uri_or_curie = self.rules.remap_prefix(
            str_or_uri_or_curie, ontology_prefix=ontology_prefix
        )

        if self.rules.str_is_blacklisted(str_or_uri_or_curie, ontology_prefix=ontology_prefix):
            raise BlacklistError

        if strict:
            return super().parse(str_or_uri_or_curie, strict=strict)
        return super().parse(str_or_uri_or_curie, strict=strict)

    @overload
    def parse_curie(
        self, curie: str, *, strict: Literal[False] = False, ontology_prefix: str | None = ...
    ) -> ReferenceTuple | None: ...

    @overload
    def parse_curie(
        self, curie: str, *, strict: Literal[True] = True, ontology_prefix: str | None = ...
    ) -> ReferenceTuple: ...

    def parse_curie(  # noqa:D102
        self, curie: str, *, strict: bool = False, ontology_prefix: str | None = None
    ) -> ReferenceTuple | None:
        if r1 := self.rules.remap_full(curie, cls=self._cls, ontology_prefix=ontology_prefix):
            return r1.pair

        # Remap node's prefix (if necessary)
        curie = self.rules.remap_prefix(curie, ontology_prefix=ontology_prefix)

        if self.rules.str_is_blacklisted(curie, ontology_prefix=ontology_prefix):
            raise BlacklistError

        if strict:
            return super().parse_curie(curie, strict=strict)
        return super().parse_curie(curie, strict=strict)
