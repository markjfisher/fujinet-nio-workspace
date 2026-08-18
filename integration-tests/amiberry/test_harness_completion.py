from conftest import (
    CompletionLogState,
    MonitorSnapshot,
    build_failure_report,
    checkpoint_progress,
    evaluate_monitor_state,
    machine_environment,
    scan_completion_log_chunk,
)


def test_machine_environment_keeps_test_args_and_settings_ordered():
    environment = machine_environment({
        "args": ["-w", "-1"],
        "settings": ["cpu_model=68030", "fpu_model=68882"],
    })
    assert environment["AMIBERRY_EXTRA_ARGS"] == "-w -1"
    assert environment["AMIBERRY_EXTRA_SETTINGS"] == (
        "cpu_model=68030;fpu_model=68882"
    )


def test_quiet_screen_before_completion_continues():
    action, reason = evaluate_monitor_state(MonitorSnapshot(
        completion_seen=False,
        requester_seen=False,
        runner_returncode=None,
        now=10.0,
        deadline=20.0,
    ))
    assert action == "continue"
    assert reason is None


def test_completion_marker_finishes_successfully():
    action, reason = evaluate_monitor_state(MonitorSnapshot(
        completion_seen=True,
        requester_seen=False,
        runner_returncode=None,
        now=10.0,
        deadline=20.0,
    ))
    assert action == "success"
    assert reason == "completion_log"


def test_marker_never_arrives_times_out():
    action, reason = evaluate_monitor_state(MonitorSnapshot(
        completion_seen=False,
        requester_seen=False,
        runner_returncode=None,
        now=20.0,
        deadline=20.0,
    ))
    assert action == "failure"
    assert reason == "timeout"


def test_failed_marker_is_not_treated_as_completion():
    chunk = (
        "2026-08-14 [I] fujibus: receive: id=8 dev=0xFE cmd=0x02 params=0 payload=24\n"
        "2026-08-14 [I] fujibus:   0000: 68 6f 73 74 3a 2f 6f 6e 65 2d 72 6f 77 00 00 00 |host:/one-row...|\n"
        "2026-08-14 [I] fujibus: send: dev=0xFE status=5 cmd=0x02 payload=0\n"
    )
    found, _ = scan_completion_log_chunk(chunk, "host:/one-row")
    assert found is False


def test_requester_before_marker_is_immediate_failure():
    action, reason = evaluate_monitor_state(MonitorSnapshot(
        completion_seen=False,
        requester_seen=True,
        runner_returncode=None,
        now=10.0,
        deadline=20.0,
    ))
    assert action == "failure"
    assert reason == "requester"


def test_runner_exit_before_marker_is_infrastructure_failure():
    action, reason = evaluate_monitor_state(MonitorSnapshot(
        completion_seen=False,
        requester_seen=False,
        runner_returncode=1,
        now=10.0,
        deadline=20.0,
    ))
    assert action == "failure"
    assert reason == "runner_exit"


def test_checkpoint_progress_identifies_last_present_and_first_missing():
    ordered = ["one.result", "two.result", "three.result"]
    present = ["one.result", "two.result"]
    assert checkpoint_progress(ordered, present) == ("two.result", "three.result")


def test_checkpoint_progress_handles_no_checkpoint_present():
    ordered = ["one.result", "two.result"]
    assert checkpoint_progress(ordered, []) == ("<none>", "one.result")


def test_failure_report_includes_guest_progress():
    report = build_failure_report(
        case_name="diskdevice-adf",
        termination_reason="timeout",
        ordered_results=["one.result", "two.result", "three.result"],
        present_results=["one.result", "two.result"],
        requester_seen=False,
        recent_activity=True,
        runner_exit_state="ipc-quit-250",
    )
    assert "termination reason: timeout" in report
    assert "last checkpoint present: two.result" in report
    assert "first checkpoint missing: three.result" in report
    assert "requester seen: no" in report
    assert "recent NIO/serial activity: yes" in report
    assert "runner exit state: ipc-quit-250" in report


def test_screenshot_quiet_does_not_change_logical_outcome():
    low = evaluate_monitor_state(MonitorSnapshot(
        completion_seen=False,
        requester_seen=False,
        runner_returncode=None,
        now=10.0,
        deadline=20.0,
    ))
    high = evaluate_monitor_state(MonitorSnapshot(
        completion_seen=False,
        requester_seen=False,
        runner_returncode=None,
        now=10.0,
        deadline=20.0,
    ))
    assert low == high == ("continue", None)


def test_completion_log_marker_within_single_row():
    chunk = (
        "2026-08-14 [I] fujibus: receive: id=1 dev=0xFE cmd=0x02 params=0 payload=20\n"
        "2026-08-14 [I] fujibus:   0000: 68 6f 73 74 3a 2f 6f 6e 65 2d 72 6f 77 00 00 00 |host:/one-row...|\n"
        "2026-08-14 [I] fujibus: send: dev=0xFE status=0 cmd=0x02 payload=0\n"
    )
    found, state = scan_completion_log_chunk(chunk, "host:/one-row")
    assert found is True
    assert isinstance(state, CompletionLogState)


def test_completion_log_marker_split_across_two_rows():
    chunk = (
        "2026-08-14 [I] fujibus: receive: id=2 dev=0xFE cmd=0x02 params=0 payload=24\n"
        "2026-08-14 [I] fujibus:   0000: 78 78 68 6f 73 74 3a 2f 74 77 6f 2d 72 6f 77 2d |xxhost:/two-row-|\n"
        "2026-08-14 [I] fujibus:   0010: 6d 61 72 6b 65 72 00 00                         |marker..|\n"
        "2026-08-14 [I] fujibus: send: dev=0xFE status=0 cmd=0x02 payload=0\n"
    )
    found, _ = scan_completion_log_chunk(chunk, "host:/two-row-marker")
    assert found is True


def test_completion_log_marker_split_across_three_rows():
    chunk = (
        "2026-08-14 [I] fujibus: receive: id=3 dev=0xFE cmd=0x02 params=0 payload=40\n"
        "2026-08-14 [I] fujibus:   0000: 01 2a 00 68 6f 73 74 3a 2f 61 6d 69 67 61 2d 65 |.*.host:/amiga-e|\n"
        "2026-08-14 [I] fujibus:   0010: 32 65 2d 63 6f 6d 70 6c 65 74 65 2f 64 69 73 6b |2e-complete/disk|\n"
        "2026-08-14 [I] fujibus:   0020: 64 65 76 69 63 65 2d 66 6d 6f 75 6e 74 00 00 a4 |device-fmount...|\n"
        "2026-08-14 [I] fujibus: send: dev=0xFE status=0 cmd=0x02 payload=10\n"
    )
    found, _ = scan_completion_log_chunk(chunk, "host:/amiga-e2e-complete/diskdevice-fmount")
    assert found is True


def test_completion_log_does_not_concatenate_adjacent_packets():
    chunk = (
        "2026-08-14 [I] fujibus: receive: id=4 dev=0xFE cmd=0x02 params=0 payload=16\n"
        "2026-08-14 [I] fujibus:   0000: 68 6f 73 74 3a 2f 74 77 6f 2d 72 6f 77 2d 6d 61 |host:/two-row-ma|\n"
        "2026-08-14 [I] fujibus: send: dev=0xFE status=0 cmd=0x02 payload=0\n"
        "2026-08-14 [I] fujibus: receive: id=5 dev=0xFE cmd=0x02 params=0 payload=16\n"
        "2026-08-14 [I] fujibus:   0000: 72 6b 65 72 00 00 00 00 00 00 00 00 00 00 00 00 |rker............|\n"
        "2026-08-14 [I] fujibus: send: dev=0xFE status=0 cmd=0x02 payload=0\n"
    )
    found, _ = scan_completion_log_chunk(chunk, "host:/two-row-marker")
    assert found is False


def test_completion_log_partial_packet_is_completed_on_next_poll():
    first = (
        "2026-08-14 [I] fujibus: receive: id=6 dev=0xFE cmd=0x02 params=0 payload=40\n"
        "2026-08-14 [I] fujibus:   0000: 01 2a 00 68 6f 73 74 3a 2f 61 6d 69 67 61 2d 65 |.*.host:/amiga-e|\n"
        "2026-08-14 [I] fujibus:   0010: 32 65 2d 63 6f 6d 70 6c 65 74 65 2f 64 69 73 6b |2e-complete/disk|\n"
    )
    second = (
        "2026-08-14 [I] fujibus:   0020: 64 65 76 69 63 65 2d 66 6d 6f 75 6e 74 00 00 a4 |device-fmount...|\n"
        "2026-08-14 [I] fujibus: send: dev=0xFE status=0 cmd=0x02 payload=10\n"
    )
    found, state = scan_completion_log_chunk(first, "host:/amiga-e2e-complete/diskdevice-fmount")
    assert found is False
    found, _ = scan_completion_log_chunk(second, "host:/amiga-e2e-complete/diskdevice-fmount", state)
    assert found is True


def test_completion_log_partial_line_is_retained_until_newline():
    first = (
        "2026-08-14 [I] fujibus: receive: id=7 dev=0xFE cmd=0x02 params=0 payload=24\n"
        "2026-08-14 [I] fujibus:   0000: 68 6f 73 74 3a 2f 6f 6e 65 2d 72 6f 77 00 00 00 |host:/one-row...|"
    )
    second = "\n2026-08-14 [I] fujibus: send: dev=0xFE status=0 cmd=0x02 payload=0\n"
    found, state = scan_completion_log_chunk(first, "host:/one-row")
    assert found is False
    found, _ = scan_completion_log_chunk(second, "host:/one-row", state)
    assert found is True
