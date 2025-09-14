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


class StringTrie(UserDict[str, str]):
    """Base trie class."""

    def __init__(self, d: dict[str, str]) -> None:
        """Create a new trie."""
        super().__init__()
        self.root = Node()
        for k, v in d.items():
            self[k] = v

    def __setitem__(self, key: str, value: str) -> None:
        node = self.root
        for part in key:
            next_node = node.children.get(part)
            if next_node is None:
                node = node.children.setdefault(part, Node())
            else:
                node = next_node
        node.value = value

    def longest_prefix_item(self, key: str) -> tuple[str, str]:
        """Return the item (``(key,value)`` tuple) associated with the longest key in this trie that is a prefix of ``key``."""
        prefix_characters: list[str] = []
        node: Node | None = self.root
        longest_prefix_value: str | None = self.root.value
        max_non_null_index = -1
        for i, character in enumerate(key):
            node = cast(Node, node).children.get(character)
            if node is None:
                break
            prefix_characters.append(character)
            if node.value is not None:
                longest_prefix_value = node.value
                max_non_null_index = i
        if longest_prefix_value is None:
            raise KeyError # TODO this shouldn't be possible
        del prefix_characters[max_non_null_index + 1 :]
        return "".join(prefix_characters), longest_prefix_value

    def _find(self, key: Sequence[str]) -> Node | None:
        node: Node | None = self.root
        for part in key:
            node = cast(Node, node).children.get(part)
            if node is None:
                break
        return node

    def __contains__(self, key: Any) -> bool:
        node = self._find(key)
        return node is not None and node.value is not None
