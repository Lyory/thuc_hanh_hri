from unittest.mock import Mock, patch

import numpy as np
import pytest

from emotion_turtlebot.face import FaceDetector, same_face
from emotion_turtlebot.node import analyze_face


def test_emotion_uses_only_the_face_crop_without_another_detector():
    deepface = Mock()
    deepface.analyze.return_value = [{'dominant_emotion': 'happy', 'emotion': {'happy': 88.0}}]
    crop = np.zeros((100, 100, 3), dtype=np.uint8)
    assert analyze_face(crop, deepface) == ('happy', 88.0)
    kwargs = deepface.analyze.call_args.kwargs
    assert kwargs['img_path'] is crop
    assert kwargs['detector_backend'] == 'skip'
    assert kwargs['actions'] == ['emotion']


def test_model_error_is_not_hidden_as_missing_face():
    deepface = Mock()
    deepface.analyze.side_effect = ValueError('bad model weights')
    with pytest.raises(ValueError, match='bad model weights'):
        analyze_face('crop', deepface)


def make_detector():
    with patch('emotion_turtlebot.face.get_package_share_directory', return_value='/test'), \
            patch('emotion_turtlebot.face.cv2.FaceDetectorYN.create') as factory:
        detector = FaceDetector()
    return detector, factory.return_value


def test_current_frame_box_is_clipped_and_largest_face_is_selected():
    detector, model = make_detector()
    model.detect.return_value = (1, np.array([
        [50, 60, 10, 10, *([0] * 10), 0.99],
        [-4.5, 10.2, 110, 120, *([0] * 10), 0.95],
    ]))
    frame = np.zeros((100, 200, 3), dtype=np.uint8)
    region = detector.detect(frame)
    assert region == {'x': 0, 'y': 10, 'w': 106, 'h': 90}
    model.setInputSize.assert_called_once_with((200, 100))
    assert model.detect.call_args.args[0] is frame


def test_no_face_returns_no_box():
    detector, model = make_detector()
    model.detect.return_value = (0, None)
    assert detector.detect(np.zeros((480, 640, 3), dtype=np.uint8)) is None


def test_lost_face_or_position_jump_invalidates_pending_emotion():
    region = {'x': 10, 'y': 20, 'w': 80, 'h': 80}
    assert same_face(region, dict(region, x=15))
    assert not same_face(region, dict(region, x=300))
    assert not same_face(region, None)
    assert not same_face(None, region)
    assert same_face(None, None)
