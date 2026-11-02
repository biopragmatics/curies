"""Test the subsetting workflow."""

import unittest

import networkx as nx

from curies import Prefix, Reference
from curies.subsetting import Descendants, GraphSubsetter, Intersection, Union

A1 = Reference.from_curie("A:1")
A2 = Reference.from_curie("A:2")
A3 = Reference.from_curie("A:3")


class TestSubsetting(unittest.TestCase):
    """A test case for the subsetting workflow."""

    def test_operations_errors(self) -> None:
        """Test operations."""
        with self.assertRaises(TypeError):
            Descendants(reference=A1) - None  # type:ignore

    def test_union(self) -> None:
        """Test union operations."""
        with self.assertRaises(TypeError):
            Descendants(reference=A1) | None  # type:ignore

        x = Descendants(reference=A1) | Descendants(reference=A2)
        self.assertEqual(Union(args=[Descendants(reference=A1), Descendants(reference=A2)]), x)
        self.assertEqual(Union.from_args(Descendants(reference=A1), Descendants(reference=A2)), x)
        self.assertEqual(
            Union(
                args=[
                    Descendants(reference=A1),
                    Descendants(reference=A2),
                    Descendants(reference=A3),
                ]
            ),
            Descendants(reference=A1)
            | Union.from_args(Descendants(reference=A2), Descendants(reference=A3)),
        )

    def test_intersection(self) -> None:
        """Test intersection operations."""
        with self.assertRaises(TypeError):
            Descendants(reference=A1) & None  # type:ignore

        x = Descendants(reference=A1) & Descendants(reference=A2)
        self.assertEqual(
            Intersection(args=[Descendants(reference=A1), Descendants(reference=A2)]), x
        )
        self.assertEqual(
            Intersection.from_args(Descendants(reference=A1), Descendants(reference=A2)), x
        )
        self.assertEqual(
            Intersection(
                args=[
                    Descendants(reference=A1),
                    Descendants(reference=A2),
                    Descendants(reference=A3),
                ]
            ),
            Descendants(reference=A1)
            & Intersection.from_args(Descendants(reference=A2), Descendants(reference=A3)),
        )

    def test_evaluation(self) -> None:
        """Test getting simple subsets."""
        alpha = Prefix("alpha")
        alphas = [Reference(prefix=alpha, identifier=str(i)) for i in range(10)]

        graph_alpha = nx.DiGraph()
        graph_alpha.add_nodes_from(alphas)
        graph_alpha.add_edge(alphas[0], alphas[1])  # A0 is a A1
        graph_alpha.add_edge(alphas[1], alphas[2])  # A1 is a A2
        graph_alpha.add_edge(alphas[2], alphas[3])  # A2 is a A3
        graph_alpha.add_edge(alphas[4], alphas[3])  # A4 is a A3
        graph_alpha.add_edge(alphas[5], alphas[6])
        graph_alpha.add_edge(alphas[6], alphas[7])

        graphs = {alpha: graph_alpha}
        evaluator = GraphSubsetter(graphs)

        with self.assertRaises(TypeError):
            evaluator.query(None)  # type:ignore

        self.assertEqual(
            set(), evaluator.query(Descendants(reference=Reference.from_curie("NOPE:NOPE")))
        )
        self.assertEqual(set(), evaluator.query(Descendants(reference=alphas[0], inclusive=False)))
        self.assertEqual(
            {alphas[0]}, evaluator.query(Descendants(reference=alphas[0], inclusive=True))
        )
        self.assertEqual(
            {alphas[0], alphas[1]},
            evaluator.query(Descendants(reference=alphas[1], inclusive=True)),
        )
        self.assertEqual(
            {alphas[0]},
            evaluator.query(Descendants(reference=alphas[1], inclusive=False)),
        )
        self.assertEqual(
            {alphas[0], alphas[1], alphas[2]},
            evaluator.query(Descendants(reference=alphas[2], inclusive=True)),
        )
        self.assertEqual(
            {alphas[0], alphas[1], alphas[2], alphas[3], alphas[4]},
            evaluator.query(Descendants(reference=alphas[3], inclusive=True)),
        )
        self.assertEqual(
            {
                alphas[0],
                alphas[1],
                alphas[2],
                alphas[3],
                alphas[4],
                alphas[5],
                alphas[6],
                alphas[7],
            },
            evaluator.query(Descendants(reference=alphas[3]) | Descendants(reference=alphas[7])),
        )
        self.assertEqual(
            {alphas[2], alphas[3], alphas[4]},
            evaluator.query(Descendants(reference=alphas[3]) - Descendants(reference=alphas[1])),
        )

        self.assertEqual(
            set(),
            evaluator.query(Descendants(reference=alphas[3]) & Descendants(reference=alphas[7])),
        )
        self.assertEqual(
            {alphas[0], alphas[1]},
            evaluator.query(Descendants(reference=alphas[3]) & Descendants(reference=alphas[1])),
        )
