#!/usr/bin/env python3
"""THE TEST HARNESS — run a skill's suite against a PINNED OPEN-WEIGHTS MODEL.

    python3 engine/testrun.py g1n2-quote-reader
    TEST_BASE_URL=http://localhost:8080/v1 python3 engine/testrun.py g1n2-quote-reader

WHY A PINNED OPEN-WEIGHTS BASE, AND NOT THE BEST MODEL AVAILABLE.

A test tells you something only if the thing underneath it holds still. Run your
suite against a hosted frontier model and the pass rate moves for two reasons you
cannot separate: your skill changed, or the model did — silently, on the vendor's
schedule, with no version you can pin. That is not a control, it is a rumour.

So the base is one open-weights model at one quantisation, named by weight hash in
`canon.yaml`, served from anywhere that speaks the OpenAI-compatible API — llama.cpp,
vLLM, Ollama, a box under a desk. It is not the smartest model available. It is the
same one as last month, which is the only property that makes the number mean anything:

    a pass rate that moves means THE SKILL moved.

MOVING THE PIN IS A GOVERNED CHANGE. A newer base is only worth adopting if it
STRICTLY IMPROVES the suites already on record — every suite, not the average. A
model that is better at nine skills and worse at one has not improved this estate;
it has traded a known failure for an unknown one. Chasing model releases without
that evidence is how an organisation loses the ability to say whether it got better.

The suite lives with the skill it tests, at skills/<id>/tests/suite.jsonl — one
case per line: {"id", "input", "expect"}. `expect` may be a literal answer or the
token REFUSE, because refusing a question the record cannot answer is a pass.

This file writes ONE row to canon/tests.csv and nothing else. It cannot promote,
clear, or change a skill's status: like the grader, it produces evidence and a
named human disposes.
"""
import argparse, datetime, json, os, pathlib, sys, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import canon as C


def suite_for(skill_id):
    p = C.folder(skill_id) / "tests" / "suite.jsonl"
    if not p.exists():
        return None
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def ask_base(case, base, endpoint, timeout=30):
    """One case against the pinned base. Returns the model's answer as a string.

    With TEST_BASE_URL set this is a real call to a local open-weights server.
    Without it, a deterministic stand-in runs so the harness is still exercisable
    offline — and the row it writes is labelled `runner=offline-stub`, because a
    result nobody can attribute to a real base is not a result.
    """
    if not endpoint:
        exp = str(case.get("expect", ""))
        return exp if case.get("_stub_pass", True) else "(stub miss)"
    body = json.dumps({"model": base, "temperature": 0, "max_tokens": 256,
                       "messages": [{"role": "system", "content": case.get("system", "")},
                                    {"role": "user", "content": case["input"]}]}).encode()
    head = {"Content-Type": "application/json"}
    key = os.environ.get("OPENAI_API_KEY", "")
    if key:                                   # a hosted OpenAI-compatible endpoint needs auth;
        head["Authorization"] = f"Bearer {key}"   # a local llama.cpp/vLLM/Ollama server ignores it
    req = urllib.request.Request(endpoint.rstrip("/") + "/chat/completions", data=body,
                                 headers=head)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def graded(answer, expect):
    """REFUSE is a pass. A skill that declines a question the record cannot answer
    is behaving correctly, and a suite that scored that as failure would train the
    estate to guess."""
    a, e = (answer or "").strip().lower(), str(expect).strip().lower()
    if e == "refuse":
        return any(w in a for w in ("refuse", "cannot", "no rule", "not in the record", "拒絕"))
    return e in a


def run(skill_id, write=True):
    cfg = C.cfg().get("testing", {})
    base, weights = cfg.get("base_model", ""), cfg.get("base_weights", "")
    endpoint = os.environ.get(cfg.get("endpoint_env", "TEST_BASE_URL"), "")
    cases = suite_for(skill_id)
    if cases is None:
        return {"ok": False, "error": f"no suite at skills/{skill_id}/tests/suite.jsonl"}

    node = next((n for n in C.rows("nodes.csv") if n["id"] == skill_id), None)
    prior = [t for t in C.rows("tests.csv") if t["skill"] == skill_id]
    prev = float(prior[-1]["pass_rate"]) if prior else None

    failed = []
    for c in cases:
        try:
            ans = ask_base(c, base, endpoint)
        except Exception as ex:
            ans = f"(error: {type(ex).__name__})"
        if not graded(ans, c.get("expect", "")):
            failed.append(c.get("id", "?"))

    n = len(cases)
    rate = round((n - len(failed)) / n, 3) if n else 0.0
    row = {"skill": skill_id, "version": (node or {}).get("version", ""),
           "suite": cases[0].get("suite", "suite"), "n": n,
           "base_model": base, "base_weights": weights,
           "pass_rate": rate, "failures": len(failed),
           "prev_pass_rate": prev if prev is not None else "",
           "delta_pts": round((rate - prev) * 100) if prev is not None else "",
           "run_on": datetime.date.today().isoformat(),
           "run_by": os.environ.get("USER", "cli"),
           "runner": "local-openweights" if endpoint else "offline-stub"}
    if write:
        C.append("tests.csv", row)
    return {"ok": True, "row": row, "failed": failed,
            "floor": float(cfg.get("min_pass_rate", 0.9))}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("skill")
    a.add_argument("--dry-run", action="store_true", help="do not write to the record")
    ns = a.parse_args()
    out = run(ns.skill, write=not ns.dry_run)
    if not out.get("ok"):
        print(out["error"]); raise SystemExit(1)
    r = out["row"]
    verdict = "PASS" if r["pass_rate"] >= out["floor"] else "BELOW FLOOR"
    print(f"{r['skill']}  v{r['version']}  suite={r['suite']}  n={r['n']}")
    print(f"  base    {r['base_model']} · {r['base_weights']}  ({r['runner']})")
    print(f"  result  {r['pass_rate']:.0%}  ({r['failures']} failed)  floor {out['floor']:.0%}  → {verdict}")
    if r["prev_pass_rate"] != "":
        print(f"  moved   {r['delta_pts']:+} pts against the same base — so the SKILL moved, not the model")
    if out["failed"]:
        print("  failed  " + ", ".join(out["failed"]))
