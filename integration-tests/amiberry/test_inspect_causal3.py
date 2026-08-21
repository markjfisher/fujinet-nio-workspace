"""Causal isolation series 3: double-inspection ordering and symmetry.

All variants share the full preamble (fmount 11, Dir, Type, doslistdiag, status)
to activate DN0, then run two consecutive diskinspect calls with no post steps
before FLS.

K: inspect 14 -> inspect 11  (original ordering, HD then live DD slot)
L: inspect 11 -> inspect 14  (reversed)
M: inspect 11 -> inspect 11  (same slot twice, DD)
N: inspect 14 -> inspect 14  (same slot twice, HD)
O: inspect 14 -> Wait 1 -> inspect 11  (timing probe for K; run only if K fails)

Pass criterion: progress.result contains "BEFORE FLS" and "AFTER FLS".
"""


def _assert_pass(results: dict, variant: str) -> None:
    prog = results["progress.result"]
    assert "PREAMBLE DONE" in prog, f"{variant}: preamble did not complete"
    assert "BEFORE FLS" in prog, f"{variant}: hung before FLS:\n{prog}"
    assert "AFTER FLS" in prog, f"{variant}: FLS did not return:\n{prog}"


def test_inspect_causal_k(run_amiga_case):
    """Preamble + inspect 14 then 11 (original ordering) -> FLS."""
    results = run_amiga_case("inspect-causal-k")
    assert "INSPECT HD RC=0" in results["inspect-hd.result"]
    assert "INSPECT DD RC=0" in results["inspect-dd.result"]
    _assert_pass(results, "K")


def test_inspect_causal_l(run_amiga_case):
    """Preamble + inspect 11 then 14 (reversed) -> FLS."""
    results = run_amiga_case("inspect-causal-l")
    assert "INSPECT DD RC=0" in results["inspect-dd.result"]
    assert "INSPECT HD RC=0" in results["inspect-hd.result"]
    _assert_pass(results, "L")


def test_inspect_causal_m(run_amiga_case):
    """Preamble + inspect 11 twice (same live slot) -> FLS."""
    results = run_amiga_case("inspect-causal-m")
    assert "INSPECT DD-1 RC=0" in results["inspect-dd-1.result"]
    assert "INSPECT DD-2 RC=0" in results["inspect-dd-2.result"]
    _assert_pass(results, "M")


def test_inspect_causal_n(run_amiga_case):
    """Preamble + inspect 14 twice (same non-live slot) -> FLS."""
    results = run_amiga_case("inspect-causal-n")
    assert "INSPECT HD-1 RC=0" in results["inspect-hd-1.result"]
    assert "INSPECT HD-2 RC=0" in results["inspect-hd-2.result"]
    _assert_pass(results, "N")


def test_inspect_causal_o(run_amiga_case):
    """Preamble + inspect 14, Wait 1, inspect 11 -> FLS (timing probe for K)."""
    results = run_amiga_case("inspect-causal-o")
    assert "INSPECT HD RC=0" in results["inspect-hd.result"]
    assert "INSPECT DD RC=0" in results["inspect-dd.result"]
    _assert_pass(results, "O")
