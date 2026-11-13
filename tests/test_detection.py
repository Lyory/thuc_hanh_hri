from unittest.mock import Mock

import pytest

from emotion_turtlebot.node import analyze_frame


def face(emotion, width):
    return {"dominant_emotion": emotion, "emotion": {emotion: 88.0},
            "region": {"x": 1, "y": 2, "w": width, "h": width}}


def test_largest_face_controls_robot_and_real_detection_is_required():
    deepface = Mock()
    deepface.analyze.return_value = [face("sad", 20), face("happy", 100)]
    emotion, confidence, region = analyze_frame("frame", deepface)
    assert (emotion, confidence, region["w"]) == ("happy", 88.0, 100)
    assert deepface.analyze.call_args.kwargs["enforce_detection"] is True
    assert deepface.analyze.call_args.kwargs["actions"] == ["emotion"]


def test_missing_face_is_not_treated_as_neutral():
    deepface = Mock()
    deepface.analyze.side_effect = ValueError("Face could not be detected in numpy array")
    assert analyze_frame("frame", deepface) == (None, 0.0, None)


def test_model_error_is_not_hidden_as_missing_face():
    deepface = Mock()
    deepface.analyze.side_effect = ValueError("bad model weights")
    with pytest.raises(ValueError, match="bad model weights"):
        analyze_frame("frame", deepface)
