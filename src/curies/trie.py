"""A trie."""

from collections import UserDict
from collections.abc import Sequence
from typing import Union

__all__ = ["StringTrie"]


class NULL:
    """A singleton sentinel that works with pickling."""


Children = dict[str, Union["Children", type[NULL]]]


class Node:
    """Trie node class."""

    __slots__ = ("children", "value")

    value: str | type[NULL]
    children: Children

    def __init__(self, value: str | type[NULL] = NULL) -> None:
        """Initialize the node."""
        self.value = value
        self.children = {}


class Trie(UserDict[str, str]):
    """Base trie class."""

    def __init__(self, d: dict[str, str]) -> None:
        """Create a new trie.

        Parameters are the same with ``dict()``.
        """
        super().__init__()
        self._root = Node()
        for k, v in d.items():
            self[k] = v

    def longest_prefix_item(self, key: str) -> tuple[str, str]:
        """Return the item (``(key,value)`` tuple) associated with the longest key in this trie that is a prefix of ``key``.

        If the trie doesn't contain any prefix of ``key``:
          - if ``default`` is given, return it
          - otherwise raise ``KeyError``
        """
        prefix: list[str] = []
        append = prefix.append
        node = self._root
        longest_prefix_value = node.value
        max_non_null_index = -1
        for i, part in enumerate(key):
            node = node.children.get(part)
            if node is None:
                break
            append(part)
            value = node.value
            if value is not NULL:
                longest_prefix_value = value
                max_non_null_index = i
        if longest_prefix_value is not NULL:
            del prefix[max_non_null_index + 1 :]
            return "".join(prefix), longest_prefix_value
        else:
            raise KeyError

    def _find(self, key: Sequence[str]) -> Node:
        node = self._root
        for part in key:
            node = node.children.get(part)
            if node is None:
                break
        return node

    def __contains__(self, key: str) -> bool:
        node = self._find(key)
        return node is not None and node.value is not NULL

    def __setitem__(self, key: str, value: str) -> None:
        node = self._root
        for part in key:
            next_node = node.children.get(part)
            if next_node is None:
                node = node.children.setdefault(part, Node())
            else:
                node = next_node
        node.value = value

    def __repr__(self) -> str:
        return "{}({{{}}})".format(
            self.__class__.__name__,
            ", ".join("{!r}: {!r}".format(*t) for t in self.iteritems()),
        )


StringTrie = Trie
