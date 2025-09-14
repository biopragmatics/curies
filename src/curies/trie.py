"""A trie, inspired from https://github.com/gsakkis/pytrie/."""

from __future__ import annotations

from collections import UserDict
from collections.abc import Sequence
from typing import Any

__all__ = ["Node", "StringTrie"]


class Node:
    """Trie node class."""

    __slots__ = ("children", "value")

    value: str | None
    children: dict[str, Node]

    def __init__(self, value: str | None = None) -> None:
        """Initialize the node."""
        self.value = value
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
        prefix: list[str] = []
        append = prefix.append
        node: Node | None = self.root
        longest_prefix_value = self.root.value
        max_non_null_index = -1
        for i, part in enumerate(key):
            if node is None:
                raise ValueError
            node = node.children.get(part)
            if node is None:
                break
            append(part)
            value = node.value
            if value is not None:
                longest_prefix_value = value
                max_non_null_index = i
        if longest_prefix_value is None:
            raise KeyError
        del prefix[max_non_null_index + 1 :]
        return "".join(prefix), longest_prefix_value

    def _find(self, key: Sequence[str]) -> Node | None:
        node: Node | None = self.root
        for part in key:
            if node is None:
                raise ValueError
            node = node.children.get(part)
            if node is None:
                break
        return node

    def __contains__(self, key: Any) -> bool:
        node = self._find(key)
        return node is not None and node.value is not None
