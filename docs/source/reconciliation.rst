Reconciliation
==============

- Remapping is when a given CURIE or URI prefix is replaced with another
- Rewiring is when the correspondence between a CURIE prefix and URI prefix is updated

CURIE Prefix Remapping
----------------------
CURIE prefix remapping is configured by a mapping from existing CURIE
prefixes to new CURIE prefixes. Several rules are applied:

1. If the value is not in the prefix map, upgrade the primary prefix and retire the existing primary prefix to a synonym
2. If the value already exists in the prefix map
   - If the value is already a prefix synonym for the target record, swap them
   - If the target is in another record, do nothing (or raise an exception)

URI Prefix Remapping
--------------------
.. todo:: write me!

Prefix Rewiring
---------------
.. todo:: write me!
