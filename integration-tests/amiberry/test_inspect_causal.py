"""Causal isolation tests for diskinspect same-slot interference.

Each variant mounts DN0, runs one or two diskinspect calls, then immediately
attempts a harmless FLS completion signal. No Dir/Type/doslistdiag intervenes.

A: DN0 on slot 11, inspect slot 14 only  (different slot, HD)
B: DN0 on slot 11, inspect slot 11 only  (same slot, DD)
C: DN0 on slot 11, inspect slot 14 then 11  (both, same as original)
D: DN0 on slot 12, inspect slot 11  (different live slot, inspect the DD slot)

Pass criterion: progress.result ends with "AFTER FLS" (FLS reached NIO and returned).
"""


def _assert_pass(results: dict) -> None:
    assert "MOUNT RC=0" in results["mount.result"]
    assert "BEFORE FLS" in results["progress.result"], (
        f"hung before FLS:\n{results['progress.result']}"
    )
    assert "AFTER FLS" in results["progress.result"], (
        f"FLS did not return:\n{results['progress.result']}"
    )


def test_inspect_causal_a(run_amiga_case):
    """DN0 on slot 11, inspect slot 14 only — different slot."""
    results = run_amiga_case("inspect-causal-a")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results)


def test_inspect_causal_b(run_amiga_case):
    """DN0 on slot 11, inspect slot 11 only — same slot."""
    results = run_amiga_case("inspect-causal-b")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results)


def test_inspect_causal_c(run_amiga_case):
    """DN0 on slot 11, inspect slot 14 then 11 — same as original test."""
    results = run_amiga_case("inspect-causal-c")
    assert "INSPECT HD RC=0" in results["inspect-hd.result"]
    assert "INSPECT DD RC=0" in results["inspect-dd.result"]
    _assert_pass(results)


def test_inspect_causal_d(run_amiga_case):
    """DN0 on slot 12 (second.adf), inspect slot 11 — different live slot."""
    results = run_amiga_case("inspect-causal-d")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results)
