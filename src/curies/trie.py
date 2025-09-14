"""A trie, inspired from https://github.com/gsakkis/pytrie/."""

from __future__ import annotations

from collections import UserDict
from collections.abc import Sequence
from typing import Any, cast

__all__ = ["Node", "StringTrie"]


class Node:
    """Trie node class."""

    __slots__ = ("children", "value")

    value: str | None
    children: dict[str, Node]

    def __init__(self, value: str | None = None) -> None:
        """Initialize the node."""
        self.value = value  # this needs to be mutable, which is why this isn't a named tuple
        self.children = {}

    def _ensure_node(self, key: str) -> Node:
        node = self
        for character in key:
            next_node: Node | None = node.children.get(character)
            if next_node is None:
                node = node.children.setdefault(character, Node())
            else:
                node = next_node
        return node

    def _find_node(self, key: Sequence[str]) -> Node | None:
        node = self
        for character in key:
            next_node = node.children.get(character)
            if next_node is None:
                return None
            node = next_node
        return node


class StringTrie(UserDict[str, str]):
    """Base trie class."""

    def __init__(self, d: dict[str, str]) -> None:
        """Create a new trie."""
        super().__init__()
        self.root = Node()
        for key, value in d.items():
            self[key] = value

    def __setitem__(self, key: str, value: str) -> None:
        self.root._ensure_node(key).value = value

    def longest_prefix_item(self, uri: str) -> tuple[str, str]:
        """Return the item (``(key,value)`` tuple) associated with the longest key in this trie that is a prefix of ``key``."""
        node: Node | None = self.root
        prefix: str | None = self.root.value
        max_non_null_index = -1
        for i, character in enumerate(uri):
            node = cast(Node, node).children.get(character)
            if node is None:
                break
            if node.value is not None:
                prefix = node.value
                max_non_null_index = i
        if prefix is None:
            raise KeyError
        identifier = uri[max_non_null_index + 1:]
        return prefix, identifier

    def __contains__(self, key: Any) -> bool:
        node = self.root._find_node(key)
        return node is not None and node.value is not None
