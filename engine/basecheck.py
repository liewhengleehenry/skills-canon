#!/usr/bin/env python3
"""THE CHALLENGE — defend the pinned base against a frontier candidate.

    python3 engine/basecheck.py                          # offline, labelled stub
    OPENAI_API_KEY=sk-... python3 engine/basecheck.py --live   # real OpenAI call

WHY OPENAI IS THE CHALLENGER AND NEVER THE BASE.

The base this estate tests against is one open-weights model at one quantisation,
pinned by weight hash, because a test means something only if the thing underneath
it holds still. A hosted frontier model does not hold still: it moves on the
vendor's schedule, with no version you can pin, and when your pass rate moves you
cannot say whether your skill broke or the model did.

That is an argument against frontier models as a BASE. It is not an argument for
ignoring them. They improve, and an estate that never re-examines its pin is not
being careful, it is being stubborn.

So the frontier model gets the role it can honestly hold here: the CANDIDATE. This
file runs every suite on record against it, at api.openai.com, and compares it to
the incumbent suite by suite.

THE ADOPTION RULE.

A candidate is adopted only if it is at least as good on EVERY suite and strictly
better on at least one. Not better on average — better on every one. A model that
wins nine suites and loses the tenth has not improved this estate; it has traded a
failure you had measured for one you have not. Averages hide exactly the regression
you built a test base to catch.

And even a clean sweep does not move the pin. This file writes a row to
canon/base_candidates.csv marked PROPOSAL, and canon.yaml is never touched. The
grader proposes and a named human disposes — the same law that governs every other
change in this record, applied to the record's own configuration.
"""
import argparse, datetime, json, os, pathlib, sys, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import canon as C
import testrun


def ask_candidate(case, model, endpoint, key, timeout=30):
    """One case against the challenger. With no key, a labelled deterministic stub."""
    if not key:
        return None                      # caller marks the whole run as stub
    body = json.dumps({"model": model, "temperature": 0, "max_tokens": 256,
                       "messages": [{"role": "system", "content": case.get("system", "")},
                                    {"role": "user", "content": case["input"]}]}).encode()
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def stub_rate(skill_id, incumbent):
    """Deterministic stand-in used ONLY when no key is present. Derived from the skill
    id so the same input always gives the same number, and never presented as a
    measurement — every row and every line of output it produces says offline-stub."""
    bump = ((sum(ord(c) for c in skill_id) % 9) - 3) / 100.0   # -0.03 .. +0.05
    return max(0.0, min(1.0, round(incumbent + bump, 3)))


def run(live=False, write=True):
    t = C.cfg().get("testing", {})
    incumbent = t.get("base_model", "")
    model = t.get("candidate_model", "gpt-4o-mini")
    endpoint = t.get("candidate_endpoint", "https://api.openai.com/v1")
    key = os.environ.get(t.get("candidate_key_env", "OPENAI_API_KEY"), "") if live else ""
    runner = "openai-live" if key else "offline-stub"

    prior = {}
    for r in C.rows("tests.csv"):
        # The incumbent must be a real measurement. A challenger beaten by a stub, or
        # beating one, has been compared against nothing.
        prev = prior.get(r["skill"])
        if prev and prev.get("runner") != "offline-stub" and r.get("runner") == "offline-stub":
            continue
        prior[r["skill"]] = r                                  # last real run on the pinned base wins

    lines = []
    for sid, inc in prior.items():
        cases = testrun.suite_for(sid)
        if not cases:
            continue
        inc_rate = float(inc["pass_rate"])
        if key:
            failed = 0
            for c in cases:
                try:
                    ans = ask_candidate(c, model, endpoint, key)
                except Exception as ex:
                    ans = f"(error: {type(ex).__name__})"
                if not testrun.graded(ans, c.get("expect", "")):
                    failed += 1
            cand_rate = round((len(cases) - failed) / len(cases), 3)
        else:
            cand_rate = stub_rate(sid, inc_rate)
        lines.append({"skill": sid, "incumbent": inc_rate, "candidate": cand_rate,
                      "delta": round((cand_rate - inc_rate) * 100)})

    worse = [l for l in lines if l["candidate"] < l["incumbent"]]
    better = [l for l in lines if l["candidate"] > l["incumbent"]]
    # STRICTLY IMPROVES: no suite regresses, and at least one improves.
    adopt = bool(lines) and not worse and bool(better)
    verdict = "ADOPT" if adopt else "REJECT"
    if worse:
        why = (f"regresses on {len(worse)} of {len(lines)} suites "
               f"({', '.join(l['skill'] for l in worse)}) — a known failure traded for an unknown one")
    elif not better:
        why = "no suite improves — nothing to gain, and a new base to re-validate"
    else:
        why = f"improves {len(better)} of {len(lines)} suites and regresses on none"

    row = {"proposal_id": f"BC-{len(C.rows('base_candidates.csv')) + 1:04d}",
           "candidate_model": model, "incumbent_model": incumbent,
           "suites": len(lines), "better": len(better), "worse": len(worse),
           "verdict": verdict, "why": why,
           "run_on": datetime.date.today().isoformat(),
           "run_by": os.environ.get("USER", "cli"), "runner": runner,
           "status": "proposal"}
    if write and lines:
        C.append("base_candidates.csv", row)
    return {"ok": bool(lines), "row": row, "lines": lines, "runner": runner}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--live", action="store_true", help="call OpenAI (needs OPENAI_API_KEY)")
    a.add_argument("--dry-run", action="store_true", help="do not write the proposal")
    ns = a.parse_args()
    out = run(live=ns.live, write=not ns.dry_run)
    if not out["ok"]:
        print("no suites on record to compare"); raise SystemExit(1)
    r = out["row"]
    print(f"BASE CHANGE PROPOSAL {r['proposal_id']}   ({out['runner']})")
    print(f"  candidate  {r['candidate_model']}   vs incumbent  {r['incumbent_model']}\n")
    print(f"  {'skill':<26}{'incumbent':>10}{'candidate':>11}{'delta':>8}")
    for l in out["lines"]:
        mark = "WORSE" if l["candidate"] < l["incumbent"] else ""
        print(f"  {l['skill']:<26}{l['incumbent']:>9.0%}{l['candidate']:>11.0%}"
              f"{l['delta']:>+7}  {mark}")
    print(f"\n  VERDICT  {r['verdict']} — {r['why']}")
    print("  A base is adopted only if it is at least as good on EVERY suite and better on one.")
    if out["runner"] == "offline-stub":
        print("\n  NOTE: offline-stub. No model was called and these are not measurements.")
        print("        Re-run with OPENAI_API_KEY set and --live for a real comparison.")
    print("\n  Written to canon/base_candidates.csv as a PROPOSAL. canon.yaml is untouched.")
    print("  A named human moves the pin.")
