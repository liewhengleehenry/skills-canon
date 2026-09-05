# Skills Canon

**A skill is a folder. The canon is the record over the folders — and one skill's whole job is to police the others.**

Every skill here is a folder this company owns: code, data, tests, and a card naming the
human who answers for it. The canon records what exists, what each skill may call, and who
signed it. On a configurable cadence, the clearance skill inspects every other skill and
**anything that has changed without a signature stops running.**

> You don't get promoted. Your skill does.

---

## Run it

```bash
git clone <this repo> && cd skills-canon
python3 app.py
# → http://localhost:8000
```

Python 3 standard library only. **No `pip install`, no database, no build step.**

**Live demo — nothing to install: https://<you>.github.io/skills-canon/**
It is fully interactive. Birth a skill from the apex, watch the cadence sweep block it for
having no signature, try to approve your own proposal and be refused, sign it, and see the
benchmark re-score. The browser runs the same five laws on in-memory state; running
`app.py` runs them against real folders and CSVs on disk.

## Watch the loop

```bash
python3 engine/inspect_skills.py                 # the weekly sweep, run by hand
python3 engine/birth.py --name tariff-checker \
        --graph G1 --type reader --owner "L. Haddad"
python3 engine/inspect_skills.py                 # the newborn is BLOCKED — never cleared
python3 engine/benchmark.py                      # graded on evidence; proposes, never writes
```

## The five laws, and where each one lives in the code

| law | enforced by |
|---|---|
| **Only the apex may birth a skill.** | `engine/birth.py` refuses any caller that is not `apex:` in `canon.yaml` |
| **Every birth lands `proposed`.** Nothing enters the canon by being created. | `birth.py` writes `status=proposed` and a row in `canon/proposals.csv` |
| **The maker may not check.** | `POST /api/promote` refuses when approver == the person who raised it |
| **Nothing runs without a written PASS.** | `engine/inspect_skills.py`; `requires` edges to `g2n0-clearance` |
| **The grader proposes, never writes.** | `engine/benchmark.py` appends to `proposals.csv` and nothing else |

Two skills are **exempt** from inspection, and the exemption is the point:
`g0-root` holds the law it would be judged by, and `g2n0-clearance` cannot clear itself —
no self-approval, ever.

## The record

```
canon.yaml            cadence · apex · governance switches
canon/
  nodes.csv           what exists · address · role · OWNER · status
  edges.csv           broader (hierarchy) · requires (dependency, enforced)
  clearance.csv       the written PASS register — who signed what, when
  runs.csv            every cadence sweep and its verdict
  usage.csv           real telemetry — every call this system made
  feedback.csv        what people reported
  proposals.csv       the maker-checker queue. Nothing enters the canon except through here.
skills/               ONE FOLDER PER SKILL — the unit
  g0-root/            G0 · the apex
  g1n0-refund-master/ G1 · N0 · governs the Refund Desk graph
  g1n1-policy-steward/  G1 · N1 · the ONLY writer of record/refund-policy.csv
  g1n2-quote-reader/  G1 · N2 · answers from the record, or refuses and names the gap
  g2n0-clearance/     G2 · N0 · inspects the others and signs the register
engine/               birth · inspect · benchmark · canon access
docs/index.html       the console — works served, and standalone on GitHub Pages
```

## The benchmark

Skills are graded on **evidence this system produced** — call volume, how many other skills
depend on them, how fresh their clearance is, and what people reported — not on anyone's
opinion.

`--llm` sends the same evidence bundle to a model for a written judgement. It is bound by
the identical rule: **it proposes; a named human disposes.** An automated grader that could
promote itself would be exactly the thing this record exists to prevent.

## Prior work disclosed

The governance pattern — apex-only birth, `proposed → active` promotion, one writer per
record, clearance as a `requires` edge — was designed by the author before this event and is
carried in as a method. All code in this repository was written during BUILDMODE 2026
(4–6 September, Taipei Expo Dome). The `SKILL.md` card format follows the open
[Agent Skills](https://agentskills.io) standard.

## Honest labelling

**MERIDIAN INSTRUMENTS 子虛儀器 is an invented company** — 子虛 means *fictitious*. Every
person, rule and figure is constructed to demonstrate the mechanism. No real organisation's
data appears anywhere in this repository.

## Licence

MIT — see [LICENSE](LICENSE).
