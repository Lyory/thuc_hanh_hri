"""Verify the target OS, actual model, OpenCV GUI and ROS transport in Docker."""

import os
import sys
from time import monotonic
from unittest.mock import Mock, patch

import cv2
import numpy as np
import rclpy
import tensorflow as tf
from deepface import DeepFace
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.executors import SingleThreadedExecutor

from emotion_turtlebot.node import EmotionTurtlebot, analyze_frame


assert os.environ["ROS_DISTRO"] == "humble"
assert sys.version_info[:2] == (3, 10)
with open("/etc/os-release", encoding="utf-8") as stream:
    assert 'VERSION_ID="22.04"' in stream.read()
assert tf.__version__ == "2.16.2"

# Execute the real neural network, not just import its dependencies.
model = DeepFace.build_model(model_name="Emotion", task="facial_attribute")
prediction = model.predict(np.zeros((1, 48, 48, 3), dtype=np.uint8))
assert np.asarray(prediction).shape == (7,)
assert np.isfinite(prediction).all()
assert float(np.sum(prediction)) > 0
frame = np.zeros((480, 640, 3), dtype=np.uint8)
assert analyze_frame(frame, DeepFace) == (None, 0.0, None)
cv2.imshow("week8 GUI check", frame)
cv2.waitKey(50)
assert cv2.getWindowProperty("week8 GUI check", cv2.WND_PROP_VISIBLE) >= 1
cv2.destroyAllWindows()
print("PASS Ubuntu 22.04 / Python 3.10 / ROS Humble / real Emotion model / OpenCV GUI")

# Isolated domain and remapped topic: never send these test commands to a robot.
os.environ["ROS_DOMAIN_ID"] = "187"
for stamped, message_type in [(False, Twist), (True, TwistStamped)]:
    rclpy.init(args=["--ros-args", "-r",
                    "/cmd_vel:=/week8_test/cmd_vel", "-p", f"stamped:={str(stamped).lower()}"])
    camera = Mock()
    camera.isOpened.return_value = True
    camera.read.return_value = (True, frame.copy())
    detector = Mock()
    detector.analyze.return_value = [{
        "dominant_emotion": "happy", "emotion": {"happy": 95.0},
        "region": {"x": 10, "y": 20, "w": 80, "h": 80},
    }]
    listener = rclpy.create_node("week8_test_listener")
    messages = []
    subscription = listener.create_subscription(
        message_type, "/week8_test/cmd_vel", messages.append, 10)
    executor = SingleThreadedExecutor()
    with patch("emotion_turtlebot.node.cv2.VideoCapture", return_value=camera):
        node = EmotionTurtlebot(detector)
        executor.add_node(node)
        executor.add_node(listener)
        deadline = monotonic() + 5
        while monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
            if any((m.twist if stamped else m).linear.x > 0 for m in messages):
                break
        assert any((m.twist if stamped else m).angular.z > 0 for m in messages)
        # Force an actual camera failure; the callback must publish zero.
        camera.read.return_value = (False, None)
        try:
            node.tick()
        except RuntimeError as exc:
            assert "Webcam" in str(exc)
        else:
            raise AssertionError("Camera failure was ignored")
        node.timer.cancel()
        deadline = monotonic() + 2
        while monotonic() < deadline:
            executor.spin_once(timeout_sec=0.05)
            if (messages[-1].twist if stamped else messages[-1]).linear.x == 0:
                break
        final = messages[-1].twist if stamped else messages[-1]
        assert (final.linear.x, final.angular.z) == (0.0, 0.0)
        executor.remove_node(node)
        node.close()
        camera.release.assert_called_once()
    executor.remove_node(listener)
    listener.destroy_node()
    executor.shutdown()
    rclpy.shutdown()
    print(f"PASS ROS {message_type.__name__}: happy motion, camera failure stop, cleanup")
