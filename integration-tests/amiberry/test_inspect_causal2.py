"""Causal isolation series 2: preamble activates DN0 before diskinspect.

All variants share the same preamble (fmount 11, Dir, Type, doslistdiag, status)
to put the DN0 handler in a genuinely-active state before the inspection.

E: inspect 11                                              -> FLS
F: inspect 11 -> doslistdiag                               -> FLS
G: inspect 11 -> doslistdiag -> status                     -> FLS
H: inspect 11 -> doslistdiag -> status -> Dir              -> FLS
I: inspect 11 -> doslistdiag -> status -> Dir -> Type      -> FLS
J: inspect 14 (control) -> doslistdiag -> status -> Dir -> Type -> FLS

Pass criterion: progress.result contains "BEFORE FLS" and "AFTER FLS".
The last step that appears in progress.result before a missing "AFTER ..." line
identifies where the hang occurred if the test fails.
"""


def _assert_pass(results: dict, variant: str) -> None:
    prog = results["progress.result"]
    assert "PREAMBLE DONE" in prog, f"{variant}: preamble did not complete"
    assert "BEFORE FLS" in prog, f"{variant}: hung before FLS:\n{prog}"
    assert "AFTER FLS" in prog, f"{variant}: FLS did not return:\n{prog}"


def test_inspect_causal_e(run_amiga_case):
    """Preamble active + inspect slot 11 -> FLS only."""
    results = run_amiga_case("inspect-causal-e")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results, "E")


def test_inspect_causal_f(run_amiga_case):
    """Preamble active + inspect slot 11 -> doslistdiag -> FLS."""
    results = run_amiga_case("inspect-causal-f")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results, "F")


def test_inspect_causal_g(run_amiga_case):
    """Preamble active + inspect slot 11 -> doslistdiag -> status -> FLS."""
    results = run_amiga_case("inspect-causal-g")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results, "G")


def test_inspect_causal_h(run_amiga_case):
    """Preamble active + inspect slot 11 -> doslistdiag -> status -> Dir -> FLS."""
    results = run_amiga_case("inspect-causal-h")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results, "H")


def test_inspect_causal_i(run_amiga_case):
    """Preamble active + inspect slot 11 -> doslistdiag -> status -> Dir -> Type -> FLS."""
    results = run_amiga_case("inspect-causal-i")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results, "I")


def test_inspect_causal_j(run_amiga_case):
    """Control: preamble active + inspect slot 14 -> full post sequence -> FLS."""
    results = run_amiga_case("inspect-causal-j")
    assert "INSPECT RC=0" in results["inspect.result"]
    _assert_pass(results, "J")
