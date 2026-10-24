"""OpenCV webcam + MediaPipe Tasks Gesture Recognizer in VIDEO mode."""
from pathlib import Path
import time

import cv2
import mediapipe as mp
import rclpy
from ament_index_python.packages import get_package_share_directory
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String

from .behavior import VALID
from .wave import WaveDetector

EDGES = ((0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
         (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14),
         (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20))


class GestureRecognitionNode(Node):
    def __init__(self):
        super().__init__('gesture_recognition_node')
        default_model = str(Path(get_package_share_directory('turtlebot4_gesture_control'))
                            / 'models/gesture_recognizer.task')
        for key, value in {'camera_index': 0, 'model_path': default_model,
                           'confidence_threshold': 0.7, 'show_window': True,
                           'frame_rate': 20.0, 'mirror': True,
                           'max_frame_age': 0.4}.items():
            self.declare_parameter(key, value)
        self.capture = self.recognizer = None
        self.show = self.get_parameter('show_window').value
        self.mirror = self.get_parameter('mirror').value
        self.threshold = self.get_parameter('confidence_threshold').value
        self.max_age = self.get_parameter('max_frame_age').value
        rate = self.get_parameter('frame_rate').value
        if not 0 < self.threshold <= 1 or rate <= 0 or self.max_age <= 0:
            raise ValueError('Invalid confidence, frame rate or maximum frame age')
        model = Path(self.get_parameter('model_path').value).expanduser()
        if not model.is_file():
            raise FileNotFoundError(f'Model missing: {model}. Run scripts/download_model.py first.')
        self.publisher = self.create_publisher(String, '/detected_gesture', 1)
        self.behavior_state = 'IDLE|Recognition only'
        self.create_subscription(String, '/robot_behavior_state', self.on_state, 1)
        self.wave = WaveDetector()
        self.timestamp = -1
        try:
            self.recognizer = mp.tasks.vision.GestureRecognizer.create_from_options(
                mp.tasks.vision.GestureRecognizerOptions(
                    base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
                    running_mode=mp.tasks.vision.RunningMode.VIDEO,
                    num_hands=1, min_hand_detection_confidence=0.6,
                    min_hand_presence_confidence=0.6, min_tracking_confidence=0.6))
            self.capture = cv2.VideoCapture(self.get_parameter('camera_index').value,
                                            cv2.CAP_V4L2)
            if not self.capture.isOpened():
                raise RuntimeError('Cannot open webcam. Check /dev/video*, permissions and camera_index.')
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if self.show:
                cv2.namedWindow('Gesture control', cv2.WINDOW_NORMAL)
            self.timer = self.create_timer(1.0 / rate, self.process_frame,
                                          clock=Clock(clock_type=ClockType.STEADY_TIME))
        except Exception:
            self.close()
            raise

    def on_state(self, message):
        self.behavior_state = message.data

    def process_frame(self):
        start = time.monotonic()
        ok, frame = self.capture.read()
        if not ok:
            self.publisher.publish(String(data='No_Hand'))
            raise RuntimeError('Webcam disconnected: robot will stop on signal timeout')
        if self.mirror:
            frame = cv2.flip(frame, 1)
        self.timestamp = max(self.timestamp + 1, int(start * 1000))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.recognizer.recognize_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), self.timestamp)
        name, score = 'No_Hand', 0.0
        if result.gestures and result.gestures[0]:
            best = max(result.gestures[0], key=lambda category: category.score)
            score = best.score
            name = best.category_name if score >= self.threshold else 'Unknown'
            if name not in VALID:
                name = 'Unknown'
        now = time.monotonic()
        # Never publish a positive command from an excessively delayed frame.
        if now - start > self.max_age:
            name = 'Unknown'
        palm = name == 'Open_Palm' and bool(result.hand_landmarks)
        # Palm during RUNNING must stop immediately, regardless of movement.
        wave_enabled = (self.behavior_state.startswith(('IDLE|', 'STOPPED|')) or
                        self.behavior_state.startswith('SELECTED|GREETING'))
        wrist = result.hand_landmarks[0][0] if palm else None
        if self.wave.update(now, wrist.x if wrist else None, wrist.y if wrist else None,
                            wave_enabled):
            name = 'Wave'
        self.publisher.publish(String(data=name))  # Heartbeat at every fresh inference.
        if self.show:
            height, width = frame.shape[:2]
            for hand in result.hand_landmarks:
                points = [(int(p.x * width), int(p.y * height)) for p in hand]
                for a, b in EDGES:
                    cv2.line(frame, points[a], points[b], (50, 200, 80), 2)
                for point in points:
                    cv2.circle(frame, point, 3, (0, 200, 255), -1)
            labels = [f'{name}  confidence: {score:.1%}', self.behavior_state,
                      'Select -> Thumb Up | Palm: STOP | Fist: cancel']
            for i, label in enumerate(labels):
                cv2.putText(frame, label, (10, 28 + i*28), cv2.FONT_HERSHEY_SIMPLEX,
                            0.53, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(frame, label, (10, 28 + i*28), cv2.FONT_HERSHEY_SIMPLEX,
                            0.53, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.imshow('Gesture control', frame)
            cv2.waitKey(1)  # HighGUI event processing only; no keyboard commands.
            if cv2.getWindowProperty('Gesture control', cv2.WND_PROP_VISIBLE) < 1:
                raise RuntimeError('Webcam window closed: ending recognition')

    def close(self):
        if self.capture is not None:
            self.capture.release()
        if self.recognizer is not None:
            self.recognizer.close()
        if self.show:
            cv2.destroyAllWindows()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = GestureRecognitionNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node:
            if rclpy.ok():
                node.publisher.publish(String(data='No_Hand'))
            node.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
