#!/usr/bin/env python3
"""THE INSPECTION — and the point is that none of it is written here.

An inspector is not a special kind of thing. `g2n0-clearance` is an ordinary skill:
a folder, a version, a named human who answers for it, minted by the apex and
promoted through the same maker-checker queue as everything else. What makes it an
inspector is that other skills declare a `requires` edge on it. Take that edge away and it is a skill nobody calls.

So this file holds NO rules. It is a loop and six checks. Every rule it applies is a
row in `canon/rules.csv`, authored by a named human, approved by a different one, and
carrying a version — which means the rules are themselves inspectable, arguable and
revocable, exactly like the skills they judge.

Rules INHERIT. A rule scoped to the apex applies to every skill beneath it. A rule
scoped to a graph master applies only to that graph's members, and a graph master may
be stricter than the root but never looser. The chain is walked through the `broader`
edges already in the record, so the hierarchy that describes the organisation is the
same hierarchy that governs it.

Exemptions are not written here either. `canon/exemptions.csv` names who granted each
one and when it must be reviewed. An exemption nobody signed is not an exemption.

AND THE PARTS AN OPEN FORMAT DOES NOT GIVE YOU. A SKILL.md standard says what a skill
LOOKS LIKE. It says nothing about the four things an enterprise actually needs, and the
checks below are how this record supplies them:

  1 METADATA THAT MATTERS HERE   card_has / card_is / card_max — which fields matter is a
                                 per-enterprise decision, declared as signed rules, not
                                 baked into a format somebody else published.
  2 A GRAPH                      requires and inspected-by edges, walked below — dependency
                                 and inspection RIGHTS, declared and enforced.
  3 IDENTITY AND ACCESS          grant_write — who may create, promote, sign and write,
                                 scoped, granted by a named human, and expiring. Including
                                 across team boundaries, where skills cross-pollinate.
  4 A STABLE TEST BASE           test_exists / test_pass_min / test_current_version /
                                 test_base_pinned — every suite runs against ONE pinned
                                 open-weights model. Hold the base still and a moving pass
                                 rate means THE SKILL moved. Chase a frontier model that
                                 changes underneath you and you can never say which moved.
"""
import datetime, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import canon as C


def card(skill_id):
    """The SKILL.md front-matter, as authored by the skill's owner."""
    p = C.folder(skill_id) / "SKILL.md"
    if not p.exists():
        return None
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if ":" in line and line.startswith("  "):
            k, _, v = line.strip().partition(":")
            out[k.strip()] = v.strip().strip('"')
    return out


def ancestry(sid, edges):
    """sid, then every skill above it via `broader`, ending at the apex.
    This is the inheritance path: a rule scoped to anything on it applies here."""
    chain, seen = [sid], {sid}
    frontier = [sid]
    while frontier:
        nxt = []
        for cur in frontier:
            for e in edges:
                if e["source_id"] == cur and e["relation"] == "broader":
                    t = e["target_id"]
                    if t not in seen:
                        seen.add(t); chain.append(t); nxt.append(t)
        frontier = nxt
    return chain


# ── the six checks. Each answers one rule row. None of them names a skill. ──
def _folder_exists(c, node, cl, param, expires, up=None):
    return None if c is not None else "NO FOLDER — the canon vouches for a skill nobody holds"

def _card_has(c, node, cl, param, expires, up=None):
    if c is None: return None                       # R-FOLDER-01 already said so
    return None if param in c else f"CARD MISSING {param}"

def _card_max(c, node, cl, param, expires, up=None):
    key, _, cap = param.partition(":")
    if c is None or key not in c: return f"CARD MISSING {key}"
    try: val = float(str(c[key]).replace(",", ""))
    except ValueError: return f"CARD {key} IS NOT A NUMBER — {c[key]!r}"
    return None if val <= float(cap) else f"{key} {c[key]} EXCEEDS THE LIMIT {cap} SET BY THIS GRAPH"

def _card_is(c, node, cl, param, expires, up=None):
    key, _, want = param.partition(":")
    if c is None: return None
    got = c.get(key, "")
    return None if got == want else f"CARD {key} IS {got or 'unset'!r}, THIS GRAPH REQUIRES {want!r}"

def _node_owner(c, node, cl, param, expires, up=None):
    return None if node.get("owner", "").strip() else "STEWARDLESS — no named human"

def _clearance_pass(c, node, cl, param, expires, up=None):
    if not cl: return "NO CLEARANCE — never inspected"
    return None if cl[-1]["verdict"] == "PASS" else f"CLEARANCE {cl[-1]['verdict']}"

def _clearance_age(c, node, cl, param, expires, up=None):
    if not cl or cl[-1]["verdict"] != "PASS": return None   # R-CLEAR-01 already said so
    lim = int(param or expires)
    age = (datetime.date.today() - datetime.date.fromisoformat(cl[-1]["date"])).days
    return None if age <= lim else f"CLEARANCE EXPIRED — {age}d old, limit {lim}"

def _test_exists(c, node, cl, param, expires, up=None):
    return None if up else "NEVER TESTED — no run against the pinned base"

def _test_pass_min(c, node, cl, param, expires, up=None):
    if not up: return None                                  # R-TEST-01 already said so
    need, got = float(param or 0.9), float(up["pass_rate"])
    if got >= need: return None
    d = up.get("delta_pts", "")
    moved = f", {int(float(d)):+d} pts against the same base" if str(d).strip() not in ("", "None") else ""
    return (f"PASS RATE {got:.0%} BELOW THE {need:.0%} FLOOR ({up['failures']} of {up['n']} "
            f"failed{moved}) — the base did not move, so the skill did")

def _test_current_version(c, node, cl, param, expires, up=None):
    if not up: return None
    return None if up.get("version") == node.get("version") else (
        f"TESTED AT v{up.get('version')}, THE RECORD HOLDS v{node.get('version')} — "
        "the suite was never re-run after the change")

def _test_base_pinned(c, node, cl, param, expires, up=None):
    """A result is only comparable if it came from the base this canon pinned."""
    if not up: return None
    t = C.cfg().get("testing", {})
    if up.get("base_model") != t.get("base_model") or up.get("base_weights") != t.get("base_weights"):
        return (f"TESTED ON {up.get('base_model')} · {up.get('base_weights')}, THE CANON PINS "
                f"{t.get('base_model')} · {t.get('base_weights')} — not a comparable result")
    return None if up.get("runner") != "offline-stub" or param == "allow-stub" else (
        "RESULT FROM THE OFFLINE STUB — no open-weights base actually answered")

def _grant_write(c, node, cl, param, expires, up=None):
    """Identity and access, as a hierarchy. A skill that writes a record must hold a
    grant naming the principal, the scope and who granted it — and grants expire."""
    if not (c or {}).get("type", "").startswith("steward"): return None   # only writers
    g = [x for x in C.rows("grants.csv") if x["scope"] == node["id"] and "write" in x["may"]]
    if not g: return f"NO WRITE GRANT — {node['id']} writes a record with nobody's authority"
    last = g[-1]
    if last["principal"] != node.get("owner"):
        return (f"GRANT NAMES {last['principal']}, THE RECORD NAMES {node.get('owner')} — "
                "the authority and the accountability are different people")
    age = (datetime.date.today() - datetime.date.fromisoformat(last["expires_on"])).days
    return None if age <= 0 else f"WRITE GRANT {last['grant_id']} EXPIRED {age}d AGO"

CHECKS = {"folder_exists": _folder_exists, "card_has": _card_has, "card_max": _card_max,
          "test_exists": _test_exists, "test_pass_min": _test_pass_min,
          "test_current_version": _test_current_version, "test_base_pinned": _test_base_pinned,
          "grant_write": _grant_write,
          "card_is": _card_is, "node_owner": _node_owner,
          "clearance_pass": _clearance_pass, "clearance_age": _clearance_age}


def inspect_one(node, clearance, rules, exemptions, edges, expires_days, tests=None):
    sid = node["id"]
    if node["type"] != "skill":
        return None

    ex = exemptions.get(sid)
    if ex:
        return {"skill": sid, "owner": node.get("owner", ""), "findings": [], "applied": [],
                "verdict": "EXEMPT",
                "why": f"{ex['reason']} — granted by {ex['granted_by']} on {ex['granted_on']}, "
                       f"review due {ex['review_on']}"}

    scopes = set(ancestry(sid, edges))
    inherited = [r for r in rules if r["scope"] in scopes]
    c = card(sid)
    cl = [x for x in clearance if x["skill"] == sid]
    up = (tests or {}).get(sid)

    findings, applied = [], []
    for r in inherited:
        fn = CHECKS.get(r["check"])
        if not fn:
            findings.append(f"UNKNOWN CHECK {r['check']} IN {r['rule_id']}"); continue
        applied.append(r["rule_id"])
        bad = fn(c, node, cl, r.get("param", ""), expires_days, up)
        if bad:
            findings.append(f"{bad}  [{r['rule_id']} · {r['severity']} · ◆ {r['authored_by']}]"
                            if r["severity"] == "block" else
                            f"WARN {bad}  [{r['rule_id']} · ◆ {r['authored_by']}]")

    blocking = [f for f in findings if not f.startswith("WARN ")]
    return {"skill": sid, "owner": node.get("owner", ""), "findings": findings,
            "applied": applied, "verdict": "PASS" if not blocking else "BLOCKED", "why": ""}


def run(trigger="manual"):
    conf = C.cfg()
    expires = int(conf.get("cadence", {}).get("clearance_expires_days", 90))
    nodes = C.rows("nodes.csv")
    clearance = C.rows("clearance.csv")
    edges = C.rows("edges.csv")
    rules = C.rows("rules.csv")
    exemptions = {e["skill"]: e for e in C.rows("exemptions.csv")}
    tests = {}
    for t in C.rows("tests.csv"): tests[t["skill"]] = t   # last run wins

    results = [r for r in (inspect_one(n, clearance, rules, exemptions, edges, expires, tests)
                           for n in nodes) if r]
    passed = [r for r in results if r["verdict"] in ("PASS", "EXEMPT")]
    blocked = [r for r in results if r["verdict"] == "BLOCKED"]
    run_id = f"R-{len(C.rows('runs.csv')) + 1:04d}"
    C.append("runs.csv", {
        "run_id": run_id, "ts": C.now(), "trigger": trigger,
        "skills_checked": len(results), "passed": len(passed), "failed": 0,
        "blocked": len(blocked),
        "note": "; ".join(f"{r['skill']}: {r['findings'][0]}" for r in blocked) or "all clear"})
    inspector = conf.get("inspector", "g2n0-clearance")   # a setting, not a constant
    for r in results:
        C.log(r["skill"], "police", r["verdict"], inspector)
    return {"run_id": run_id, "results": results, "rules_in_force": len(rules),
            "passed": len(passed), "blocked": len(blocked)}


if __name__ == "__main__":
    out = run("cli")
    print(f"{out['run_id']}  checked {len(out['results'])}  PASS {out['passed']}  "
          f"BLOCKED {out['blocked']}  ·  {out['rules_in_force']} rules in force, "
          f"none of them written in this file")
    for r in out["results"]:
        mark = {"PASS": "✓", "EXEMPT": "·", "BLOCKED": "✗"}[r["verdict"]]
        applied = f"   [{len(r['applied'])} rules applied]" if r.get("applied") else ""
        print(f"  {mark} {r['skill']:<24} ◆ {r['owner']}{applied}")
        if r.get("why"):
            print(f"      → exempt: {r['why']}")
        for f in r["findings"]:
            print(f"      → {f}")
