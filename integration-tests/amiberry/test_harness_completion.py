from conftest import (
    MonitorSnapshot,
    build_failure_report,
    checkpoint_progress,
    evaluate_monitor_state,
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
