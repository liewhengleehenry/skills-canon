---
name: g1n3-legacy-fx-lookup
description: "G1·N3 · THE LEGACY READER — returns a historical FX rate against a refund quote. Superseded by g1n2-quote-reader; clearance lapsed 2026-04-02."
metadata:
  version: "2026-04.1"
  address: "G1 · N3"
  type: "reader (read-only)"
  skill-owner: "J. Varga"
  steward-type: "human"
  max-tokens: "32000"
  status: "active"
  problem: "refund quotes raised before the policy record existed still cite FX rates"
  graph: "G1 — Refund Desk"
  broader: "g1n0-refund-master"
  requires: "g2n0-clearance"
---

# g1n3-legacy-fx-lookup

Reads a historical FX rate and returns it against a refund quote.

## Superseded — and still here on purpose

`g1n2-quote-reader` answers this from the current record. This folder is kept because
**retiring a skill is a decision a named human takes**, not one the grader takes for them.
`engine/benchmark.py` has proposed its retirement; the proposal sits at `proposed` in
`canon/proposals.csv` until J. Varga or someone else signs it off.

## Registration — the obligation this card carries

Like every skill this apex issues, it registers with the record on every invocation, before
doing any work:

```python
from register import require
require("g1n3-legacy-fx-lookup", "2026-04.1", caller=<the calling system>)
```

Its clearance was signed by D. Halim on **2026-04-02** and has not been renewed. Against the
90-day limit in `canon.yaml` that is 156 days, so the record **refuses the registration** and
the skill does not run:

```
REFUSED  g1n3-legacy-fx-lookup  v2026-04.1
         CLEARANCE EXPIRED — signed 2026-04-02, 156d against a 90d limit
```

Nobody disabled it. Nobody remembered to. The signature simply expired, and the record stopped
answering for it.
