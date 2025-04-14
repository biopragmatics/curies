"""Reusable configuration."""

from typing import TypeVar
from pathlib import Path

from curies import ReferenceTuple
from pydantic import BaseModel, Field
from .api import Reference, Converter
from typing_extensions import Self

__all__ = [
    "Blacklist",
    "Rewrites",
    "Rules",
    "BlacklistError",
    "PreprocessingConverter",
]

X = TypeVar("X", bound=Reference)


class Blacklist(BaseModel):
    """A model for prefix and full blacklists."""

    full: list[str]
    resource_full: dict[str, list[str]]
    prefix: list[str]
    resource_prefix: dict[str, list[str]]
    suffix: list[str]

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


class Rewrites(BaseModel):
    """A model for prefix and full rewrites."""

    full: dict[str, str] = Field(..., description="Global remappings for an entire string")
    resource_full: dict[str, dict[str, str]] = Field(
        ..., description="Resource-keyed remappings for an entire string"
    )
    prefix: dict[str, str] = Field(..., description="Global remappings of just the prefix")
    resource_prefix: dict[str, dict[str, str]] = Field(
        ..., description="Resource-keyed remappings for just a prefix"
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
                    return new_prefix + str_or_curie_or_uri[len(old_prefix):]
        for old_prefix, new_prefix in self.prefix.items():
            if str_or_curie_or_uri.startswith(old_prefix):
                return new_prefix + str_or_curie_or_uri[len(old_prefix):]
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

    def str_has_blacklisted_prefix(
        self, str_or_curie_or_uri: str, *, ontology_prefix: str | None = None
    ) -> bool:
        """Check if the CURIE string has a blacklisted prefix."""
        return self.blacklists.str_has_blacklisted_prefix(
            str_or_curie_or_uri, ontology_prefix=ontology_prefix
        )

    def str_has_blacklisted_suffix(self, str_or_curie_or_uri: str) -> bool:
        """Check if the CURIE string has a blacklisted suffix."""
        return self.blacklists.str_has_blacklisted_suffix(str_or_curie_or_uri)

    def str_is_blacklisted_full(
        self, str_or_curie_or_uri: str, *, ontology_prefix: str | None = None
    ) -> bool:
        """Check if the full CURIE string is blacklisted."""
        return self.blacklists.str_is_blacklisted_full(
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
        rules = Rules.model_validate_json(rules)
    return rules


class BlacklistError(ValueError):
    """An error for blacklist."""


class PreprocessingConverter(Converter):
    """A converter with pre-processing rules."""

    def __init__(self, *args: Any, rules: Rules | str | Path, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.rules = _load_rules(rules)

    def from_converter(cls, converter: Converter, rules: Rules | str | Path) -> Self:
        rules = _load_rules(rules)
        return cls(rcords=converter.records, rules=rules)

    def parse(self, uri_or_curie: str, *, strict: bool, ontology_prefix: str | None = None) -> ReferenceTuple | None:
        if r1 := self.rules.remap_full(uri_or_curie, ontology_prefix=ontology_prefix):
            return r1

        # Remap node's prefix (if necessary)
        uri_or_curie = self.rules.remap_prefix(uri_or_curie, ontology_prefix=ontology_prefix)

        if self.rules.str_is_blacklisted(uri_or_curie, ontology_prefix=ontology_prefix):
            raise BlacklistError

        return super().parse(uri_or_curie, strict=strict)
