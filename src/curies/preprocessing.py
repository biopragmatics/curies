"""Reusable configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar, overload

from pydantic import BaseModel, Field
from typing_extensions import Never, Self, TypeAlias

from .api import Converter, Reference, ReferenceTuple

__all__ = [
    "BlockAction",
    "BlocklistError",
    "PreprocessingBlocklists",
    "PreprocessingConverter",
    "PreprocessingRewrites",
    "PreprocessingRules",
]

#: The action taken when the blocklist is invoked
BlockAction: TypeAlias = Literal["raise", "pass"]
X = TypeVar("X", bound=Reference)


class PreprocessingBlocklists(BaseModel):
    """A model for prefix and full blocklists."""

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

    def str_has_blocked_prefix(
        self, str_or_curie_or_uri: str, *, context: str | None = None
    ) -> bool:
        """Check if the CURIE string has a blocklisted prefix."""
        if context:
            prefixes: list[str] = self.resource_prefix.get(context, [])
            if prefixes and any(str_or_curie_or_uri.startswith(prefix) for prefix in prefixes):
                return True
        return any(str_or_curie_or_uri.startswith(prefix) for prefix in self.prefix)

    def str_has_blocked_suffix(self, str_or_curie_or_uri: str) -> bool:
        """Check if the CURIE string has a blocklisted suffix."""
        return any(str_or_curie_or_uri.endswith(suffix) for suffix in self.suffix)

    def str_is_blocked_full(self, str_or_curie_or_uri: str, *, context: str | None = None) -> bool:
        """Check if the full CURIE string is blocklisted."""
        if context and str_or_curie_or_uri in self.resource_full.get(context, set()):
            return True
        return str_or_curie_or_uri in self.full

    def str_is_blocked(self, str_or_curie_or_uri: str, *, context: str | None = None) -> bool:
        """Check if the full CURIE string is blocklisted."""
        return (
            self.str_has_blocked_prefix(str_or_curie_or_uri, context=context)
            or self.str_has_blocked_suffix(str_or_curie_or_uri)
            or self.str_is_blocked_full(str_or_curie_or_uri, context=context)
        )


class PreprocessingRewrites(BaseModel):
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
        self,
        str_or_curie_or_uri: str,
        reference_cls: type[X],
        *,
        context: str | None = None,
    ) -> X | None:
        """Remap the string if possible otherwise return it."""
        if context:
            resource_rewrites: dict[str, str] = self.resource_full.get(context, {})
            if resource_rewrites and str_or_curie_or_uri in resource_rewrites:
                return reference_cls.from_curie(resource_rewrites[str_or_curie_or_uri])

        if str_or_curie_or_uri in self.full:
            return reference_cls.from_curie(self.full[str_or_curie_or_uri])

        return None

    def remap_prefix(self, str_or_curie_or_uri: str, *, context: str | None = None) -> str:
        """Remap a prefix."""
        if context is not None:
            for old_prefix, new_prefix in self.resource_prefix.get(context, {}).items():
                if str_or_curie_or_uri.startswith(old_prefix):
                    return new_prefix + str_or_curie_or_uri[len(old_prefix) :]
        for old_prefix, new_prefix in self.prefix.items():
            if str_or_curie_or_uri.startswith(old_prefix):
                return new_prefix + str_or_curie_or_uri[len(old_prefix) :]
        return str_or_curie_or_uri


class PreprocessingRules(BaseModel):
    """A model for blocklists and rewrites."""

    blocklists: PreprocessingBlocklists
    rewrites: PreprocessingRewrites

    @classmethod
    def lint_file(cls, path: str | Path) -> None:
        """Lint a file, in place, given a file path."""
        path = Path(path).expanduser().resolve()
        rules = cls.model_validate_json(path.read_text())
        rules.blocklists._sort()
        path.write_text(
            json.dumps(
                rules.model_dump(exclude_unset=True, exclude_defaults=True),
                sort_keys=True,
                indent=2,
            )
        )

    def str_is_blocked(self, str_or_curie_or_uri: str, *, context: str | None = None) -> bool:
        """Check if the CURIE string is blocked."""
        return self.blocklists.str_is_blocked(str_or_curie_or_uri, context=context)

    def remap_full(
        self,
        str_or_curie_or_uri: str,
        reference_cls: type[X],
        *,
        context: str | None = None,
    ) -> X | None:
        """Remap the string if possible otherwise return it."""
        return self.rewrites.remap_full(
            str_or_curie_or_uri, reference_cls=reference_cls, context=context
        )

    def remap_prefix(self, str_or_curie_or_uri: str, *, context: str | None = None) -> str:
        """Remap a prefix."""
        return self.rewrites.remap_prefix(str_or_curie_or_uri, context=context)


def _load_rules(rules: str | Path | PreprocessingRules) -> PreprocessingRules:
    # TODO load remote?
    if isinstance(rules, (str, Path)):
        rules = Path(rules).expanduser().resolve()
        rules = PreprocessingRules.model_validate_json(rules.read_text())
    return rules


class BlocklistError(ValueError):
    """An error for block list."""


def _identity(x: str) -> str:
    return x


class PreprocessingConverter(Converter):
    """A converter with pre-processing rules."""

    def __init__(
        self,
        *args: Any,
        rules: PreprocessingRules | str | Path,
        reference_cls: type[X] | None = None,
        preclean: Callable[[str], str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Instantiate a converter with a ruleset for pre-processing.

        :param args: Positional arguments passed to :meth:`curies.Converter.__init__`
        :param rules: A set of rules
        :param reference_cls: The reference class to use. Defaults to
            :class:`curies.Reference`.
        :param preclean: An optional function used to preprocess strings, CURIEs, and
            URIs before parsing
        :param kwargs: Keyword arguments passed to :meth:`curies.Converter.__init__`
        """
        super().__init__(*args, **kwargs)
        self.rules = _load_rules(rules)
        self._reference_cls = Reference if reference_cls is None else reference_cls
        self._preclean = preclean if preclean is not None else _identity

    @classmethod
    def from_converter(cls, converter: Converter, rules: PreprocessingRules | str | Path) -> Self:
        """Wrap a converter with a ruleset.

        :param converter: A pre-instantiated converter
        :param rules: A pre-processing rules object, or path to a JSON file containing a
            pre-processing configuration

        :returns: A converter that uses the ruls for pre-processing when parsing URIs
            and CURIEs.
        """
        return cls(records=converter.records, rules=rules)

    # docstr-coverage:excused `overload`
    @overload
    def parse(
        self,
        str_or_uri_or_curie: str,
        *,
        strict: Literal[True] = True,
        context: str | None = ...,
        block_action: BlockAction = ...,
    ) -> ReferenceTuple: ...

    # docstr-coverage:excused `overload`
    @overload
    def parse(
        self,
        str_or_uri_or_curie: str,
        *,
        strict: Literal[False] = False,
        context: str | None = ...,
        block_action: BlockAction = ...,
    ) -> ReferenceTuple | None: ...

    def parse(
        self,
        str_or_uri_or_curie: str,
        *,
        strict: bool = False,
        context: str | None = None,
        block_action: BlockAction = "raise",
    ) -> ReferenceTuple | None:
        """Parse a string, CURIE, or URI."""
        str_or_uri_or_curie = self._preclean(str_or_uri_or_curie)

        if r1 := self.rules.remap_full(
            str_or_uri_or_curie, reference_cls=self._reference_cls, context=context
        ):
            return r1.pair

        # Remap node's prefix (if necessary)
        str_or_uri_or_curie = self.rules.remap_prefix(str_or_uri_or_curie, context=context)

        if self.rules.str_is_blocked(str_or_uri_or_curie, context=context):
            if block_action == "raise":
                raise BlocklistError
            else:
                return None

        if strict:
            return super().parse(str_or_uri_or_curie, strict=strict)
        return super().parse(str_or_uri_or_curie, strict=strict)

    # docstr-coverage:excused `overload`
    @overload
    def parse_curie(
        self,
        curie: str,
        *,
        strict: Literal[False] = False,
        context: str | None = ...,
        block_action: BlockAction = ...,
    ) -> ReferenceTuple | None: ...

    # docstr-coverage:excused `overload`
    @overload
    def parse_curie(
        self,
        curie: str,
        *,
        strict: Literal[True] = True,
        context: str | None = ...,
        block_action: BlockAction = ...,
    ) -> ReferenceTuple: ...

    def parse_curie(
        self,
        curie: str,
        *,
        strict: bool = False,
        context: str | None = None,
        block_action: BlockAction = "raise",
    ) -> ReferenceTuple | None:
        """Parse and standardize a CURIE.

        :param curie: The CURIE to parse and standardize
        :param strict: If the CURIE can't be parsed, should an error be thrown? Defaults
            to false.
        :param context: Is there a context, e.g., an ontology prefix that should be
            applied to the remapping and blocklist rules?
        :param block_action: What action should be taken when the blocklist is invoked?

            - **raise** - raise an exception
            - **pass** - return ``None``

        :returns: A tuple representing a parsed and standardized CURIE

        :raises BlocklistError: If the CURIE is blocked
        """
        curie = self._preclean(curie)

        if r1 := self.rules.remap_full(curie, reference_cls=self._reference_cls, context=context):
            return r1.pair

        # Remap node's prefix (if necessary)
        curie = self.rules.remap_prefix(curie, context=context)

        if self.rules.str_is_blocked(curie, context=context):
            if block_action == "raise":
                raise BlocklistError
            else:
                return None

        if strict:
            return super().parse_curie(curie, strict=strict)
        return super().parse_curie(curie, strict=strict)

    # docstr-coverage:excused `overload`
    @overload
    def parse_uri(
        self,
        uri: str,
        *,
        strict: Literal[False] = False,
        return_none: Literal[False] = False,
        context: str | None = ...,
        block_action: BlockAction = ...,
    ) -> Never: ...

    # docstr-coverage:excused `overload`
    @overload
    def parse_uri(
        self,
        uri: str,
        *,
        strict: Literal[False] = False,
        return_none: Literal[True] = True,
        context: str | None = ...,
        block_action: BlockAction = ...,
    ) -> ReferenceTuple | None: ...

    # docstr-coverage:excused `overload`
    @overload
    def parse_uri(
        self,
        uri: str,
        *,
        strict: Literal[True] = True,
        return_none: bool = False,
        context: str | None = ...,
        block_action: BlockAction = ...,
    ) -> ReferenceTuple: ...

    def parse_uri(
        self,
        uri: str,
        *,
        strict: bool = False,
        return_none: bool = True,
        context: str | None = None,
        block_action: BlockAction = "raise",
    ) -> ReferenceTuple | tuple[None, None] | None:
        """Parse and standardize a URI.

        :param uri: The URI to parse and standardize
        :param strict: If the URI can't be parsed, should an error be thrown? Defaults
            to false.
        :param return_none: A dummy value, do not use. If given as False, will raise a
            not implemented error
        :param context: Is there a context, e.g., an ontology prefix that should be
            applied to the remapping and blocklist rules?
        :param block_action: What action should be taken when the blocklist is invoked?

            - **raise** - raise an exception
            - **pass** - return ``None``

        :returns: A tuple representing a parsed and standardized URI

        :raises BlocklistError: If the URI is blocked
        :raises NotImplementedError: If return_none is given as False
        """
        if not return_none:
            raise NotImplementedError

        uri = self._preclean(uri)

        if r1 := self.rules.remap_full(uri, reference_cls=self._reference_cls, context=context):
            return r1.pair

        # Remap node's prefix (if necessary)
        uri = self.rules.remap_prefix(uri, context=context)

        if self.rules.str_is_blocked(uri, context=context):
            if block_action == "raise":
                raise BlocklistError
            elif return_none:
                return None

        if strict:
            return super().parse_uri(uri, strict=strict, return_none=True)
        return super().parse_uri(uri, strict=strict, return_none=True)
