#!/usr/bin/env python3
"""THE CLIENT SIDE OF THE OBLIGATION — 35 lines, standard library.

Every skill this apex issues carries this call. It runs on every invocation,
BEFORE the skill does its work, and the skill does nothing if the record says no.

    from register import register
    register("g1n2-quote-reader", "2026-08.2", caller="refund-desk-bot")

That is the whole contract. A team in another building, in another language, on
another stack, implements the same four fields over HTTP. What they cannot do is
run a skill the record has never seen, or a version it does not hold.
"""
import json, os, sys, urllib.request

CANON = os.environ.get("SKILLS_CANON", "http://localhost:8000")

def register(skill, version, caller="unknown", action="invoke", timeout=5):
    body = json.dumps({"skill": skill, "version": version,
                       "caller": caller, "action": action}).encode()
    req = urllib.request.Request(CANON + "/api/use", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

class Refused(RuntimeError): pass

def require(skill, version, caller="unknown"):
    """Register, or refuse to run. This is the line that makes the record binding."""
    a = register(skill, version, caller)
    if not a.get("ok"): raise Refused(f"{skill} @ {version}: {a.get('reason')}")
    return a

if __name__ == "__main__":
    print(json.dumps(register(*sys.argv[1:3], caller="cli"), indent=2))
