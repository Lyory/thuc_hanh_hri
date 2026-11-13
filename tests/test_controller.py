from math import tau

import pytest

from emotion_turtlebot.controller import Controller, MOTIONS


def confirm(controller, emotion, start=0.0):
    for i in range(3):
        now = start + i * 0.1
        controller.observe(emotion, 90.0, now, now)
    return now


@pytest.mark.parametrize("emotion,velocity", [
    ("happy", (0.10, 0.40)), ("sad", (0.10, -0.40)),
    ("neutral", (0.0, 0.0)), ("angry", (-0.08, 0.0)),
    ("surprise", (0.0, 0.60)), ("fear", (0.08, 0.0)),
])
def test_all_six_mappings(emotion, velocity):
    controller = Controller()
    now = confirm(controller, emotion)
    assert controller.command(now) == velocity


def test_requires_consecutive_samples_and_stops_during_transition():
    controller = Controller()
    controller.observe("happy", 90, 0, 0)
    controller.observe("sad", 90, 0.1, 0.1)
    controller.observe("happy", 90, 0.2, 0.2)
    assert controller.command(0.2) == (0, 0)
    confirm(controller, "happy", 0.3)
    assert controller.command(0.5)[0] > 0
    controller.observe("sad", 90, 0.6, 0.6)
    assert controller.command(0.6) == (0, 0)


def test_neutral_stops_immediately():
    controller = Controller()
    confirm(controller, "happy")
    controller.observe("neutral", 90, 0.3, 0.3)
    assert controller.command(0.3) == (0, 0)


@pytest.mark.parametrize("emotion,confidence", [
    (None, 0), ("disgust", 99), ("happy", 49),
    ("happy", float("nan")), ("happy", float("inf")),
])
def test_invalid_recognition_stops_and_resets_filter(emotion, confidence):
    controller = Controller()
    confirm(controller, "happy")
    controller.observe(emotion, confidence, 0.3, 0.3)
    assert controller.command(0.3) == (0, 0)
    controller.observe("happy", 90, 0.4, 0.4)
    assert controller.command(0.4) == (0, 0)


def test_stale_results_and_watchdog_stop():
    controller = Controller()
    confirm(controller, "happy")
    assert controller.command(3) == (0, 0)
    controller.observe("happy", 90, 0.4, 3)
    assert controller.command(3) == (0, 0)
    assert controller.count == 0


@pytest.mark.parametrize("emotion", ["angry", "fear", "surprise"])
def test_finite_actions_stop_and_do_not_repeat_until_expression_changes(emotion):
    controller = Controller()
    start = confirm(controller, emotion)
    duration = MOTIONS[emotion][2]
    for i in range(1, int(duration / 0.1) + 5):
        now = start + i * 0.1
        controller.observe(emotion, 90, now, now)
        if now >= start + duration:
            assert controller.command(now) == (0, 0)
        else:
            assert controller.command(now) != (0, 0)
    controller.observe("neutral", 90, now + 0.1, now + 0.1)
    restart = confirm(controller, emotion, now + 0.2)
    assert controller.command(restart) != (0, 0)


def test_surprise_duration_integrates_to_one_revolution():
    _, omega, duration = MOTIONS["surprise"]
    assert omega * duration == pytest.approx(tau)


def test_tracking_loss_does_not_restart_finite_action():
    controller = Controller()
    confirm(controller, "fear")
    controller.observe(None, 0, 0.3, 0.3)
    now = confirm(controller, "fear", 2)
    assert controller.command(now) == (0, 0)


def test_observation_gap_resets_filter_even_without_command_call():
    controller = Controller()
    controller.observe("happy", 90, 0, 0)
    controller.observe("happy", 90, 0.1, 0.1)
    controller.observe("happy", 90, 3, 3)
    assert controller.command(3) == (0, 0)
