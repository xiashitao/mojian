"""On-demand correctness eval for the consultation reply.

Not part of the unit-test suite — it hits the real LLM pipeline (slow, costs
money). Run manually:

    PYTHONPATH=. python -m web.backend.eval.run            # all cases
    PYTHONPATH=. python -m web.backend.eval.run tongling-1997   # one case

The premise: the deterministic engine is the *oracle of truth*. We never ask the
judge whether a 命理 verdict is "correct" (unanswerable) — only whether the reply
is **faithful to the engine's facts** and **a good answer to the question**, both
of which an LLM judge can assess reliably.
"""
