"""Constants for testing."""

import unittest

RUN_SLOW = False
SLOW = unittest.skipUnless(RUN_SLOW, reason="Skipping slow tests")
