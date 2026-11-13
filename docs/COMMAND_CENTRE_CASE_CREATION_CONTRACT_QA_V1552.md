# v155.2: Full frontend contract realignment for bounded authorized case reuse

The v155.1 build progressed further but two legacy frontend static checks retained the old "active_candidates" variable name for duplicate case lookup. Both checks are updated to require the new newest-first authorized SQL selection and second _visible guard. Application authorization and casework behavior are unchanged from v155.0. Backend isolated regression tests and frontend contracts remain mandatory. No DB migration or real casework changes.
