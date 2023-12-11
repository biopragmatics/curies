"""Constants for testing."""

import unittest

RUN_SLOW = True
SLOW = unittest.skipUnless(RUN_SLOW, reason="Skipping slow tests")
