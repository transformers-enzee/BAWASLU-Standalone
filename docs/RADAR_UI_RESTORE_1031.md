# v103.1 Restore previously approved Smart Radar V6.2 UI

User correction: Smart Radar's user interface must remain the approved historical Radar pilot. Restore the exact page from d70d42fc13c7, without an Inbox campaign selector or Inbox evidence panels. Preserve the independent backend source-lineage utilities for future engineering and tests but do not surface them in Radar. Add a UI guard in CI. Remaining #12 summaries and #14 accuracy are separate from the Radar UI, and #13 must not be reported complete via a UI the user rejected.
