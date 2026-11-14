"""Detect the face on the displayed frame, independently of emotion inference."""

from math import ceil, floor
from pathlib import Path

import cv2
from ament_index_python.packages import get_package_share_directory


class FaceDetector:
    def __init__(self):
        model = Path(get_package_share_directory("emotion_turtlebot")) / "models"
        self.detector = cv2.FaceDetectorYN.create(
            str(model / "face_detection_yunet_2023mar.onnx"), "", (640, 480), 0.7, 0.3, 5000,
        )

    def detect(self, frame):
        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(frame)
        if faces is None or len(faces) == 0:
            return None
        face = max(faces, key=lambda f: f[2] * f[3])
        x1, y1 = max(0, floor(face[0])), max(0, floor(face[1]))
        x2 = min(width, ceil(face[0] + face[2]))
        y2 = min(height, ceil(face[1] + face[3]))
        if x2 <= x1 or y2 <= y1:
            return None
        return {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1}


def same_face(previous, current):
    """Reject old emotion results after losing the face or a large position jump."""
    if previous is None or current is None:
        return previous is current
    width = max(0, min(previous["x"] + previous["w"], current["x"] + current["w"])
                - max(previous["x"], current["x"]))
    height = max(0, min(previous["y"] + previous["h"], current["y"] + current["h"])
                 - max(previous["y"], current["y"]))
    intersection = width * height
    union = previous["w"] * previous["h"] + current["w"] * current["h"] - intersection
    return intersection / union >= 0.2
