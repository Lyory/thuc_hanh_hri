"""Webcam + DeepFace worker and a 20 Hz ROS velocity publisher."""

from queue import Empty, Queue
from threading import Thread
from time import monotonic

import cv2
import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, HistoryPolicy

from emotion_turtlebot.controller import Controller


def analyze_frame(frame, deepface):
    """Require a real detected face; control the largest face when several exist."""
    try:
        faces = deepface.analyze(
            img_path=frame, actions=["emotion"], detector_backend="opencv",
            enforce_detection=True, silent=True,
        )
    except ValueError as exc:
        if "Face could not be detected" in str(exc):
            return None, 0.0, None
        raise
    if not faces:
        return None, 0.0, None
    face = max(faces, key=lambda f: f["region"]["w"] * f["region"]["h"])
    emotion = face["dominant_emotion"]
    return emotion, float(face["emotion"][emotion]), face["region"]


def inference_worker(frames, results, deepface):
    while True:
        captured_at, frame = frames.get()
        try:
            result = (*analyze_frame(frame, deepface), None)
        except Exception as exc:
            result = (None, 0.0, None, str(exc))
        # Only one frame is in flight; the main thread consumes before submitting.
        results.put((captured_at, *result))


class EmotionTurtlebot(Node):
    def __init__(self, deepface):
        super().__init__("emotion_turtlebot")
        camera_index = self.declare_parameter("camera_index", 0).value
        stamped = self.declare_parameter("stamped", False).value
        self.message_type = TwistStamped if stamped else Twist
        self.publisher = self.create_publisher(
            self.message_type, "/cmd_vel",
            QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=1),
        )
        self.controller = Controller()
        self.frames = Queue(maxsize=1)
        self.results = Queue(maxsize=1)
        self.busy = False
        self.emotion, self.confidence, self.region = None, 0.0, None
        self.camera = cv2.VideoCapture(camera_index)
        if not self.camera.isOpened():
            self.camera.release()
            self.destroy_node()
            raise RuntimeError(f"Cannot open webcam {camera_index}")
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        Thread(target=inference_worker, args=(self.frames, self.results, deepface),
               daemon=True).start()
        self.window = "Emotion TurtleBot | Q / ESC: quit"
        self.timer = self.create_timer(0.05, self.tick)
        self.get_logger().info("Camera ready; waiting for stable facial expression.")

    def publish_velocity(self, linear=0.0, angular=0.0):
        message = self.message_type()
        velocity = message
        if isinstance(message, TwistStamped):
            message.header.stamp = self.get_clock().now().to_msg()
            velocity = message.twist
        velocity.linear.x = linear
        velocity.angular.z = angular
        self.publisher.publish(message)

    def tick(self):
        ok, frame = self.camera.read()
        if not ok:
            self.controller.invalidate()
            self.publish_velocity()
            raise RuntimeError("Webcam disconnected or frame capture failed")
        now = monotonic()
        try:
            captured_at, emotion, confidence, region, error = self.results.get_nowait()
        except Empty:
            pass
        else:
            self.busy = False
            if error:
                self.controller.invalidate()
                self.publish_velocity()
                raise RuntimeError(f"DeepFace inference failed: {error}")
            self.emotion, self.confidence, self.region = emotion, confidence, region
            self.controller.observe(emotion, confidence, captured_at, now)
        if not self.busy:
            self.frames.put_nowait((now, frame.copy()))
            self.busy = True

        linear, angular = self.controller.command(now)
        self.publish_velocity(linear, angular)
        fresh = now - self.controller.last_seen <= self.controller.timeout
        if fresh and self.region is not None:
            x, y, w, h = (self.region[k] for k in ("x", "y", "w", "h"))
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        valid = fresh and self.emotion is not None
        label = f"{self.emotion}: {self.confidence:.1f}%" if valid else "No valid face / waiting"
        status = f"v={linear:+.2f} m/s  w={angular:+.2f} rad/s"
        cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                    0.65, (0, 255, 255), 2)
        cv2.putText(frame, status, (10, 55), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0, 255, 255), 2)
        cv2.imshow(self.window, frame)
        if cv2.waitKey(1) & 0xFF in (27, ord("q")):
            raise KeyboardInterrupt
        if cv2.getWindowProperty(self.window, cv2.WND_PROP_VISIBLE) < 1:
            raise KeyboardInterrupt

    def close(self):
        self.timer.cancel()
        # Send stop while the context is still usable (Q, camera/model error).
        if self.context.ok():
            for _ in range(3):
                self.publish_velocity()
        self.camera.release()
        cv2.destroyAllWindows()
        self.destroy_node()


def main(args=None):
    # Import lazily so package discovery/tests do not initialize TensorFlow.
    from deepface import DeepFace

    # Load/download weights before opening the camera or starting motion control.
    DeepFace.build_model(model_name="Emotion", task="facial_attribute")
    rclpy.init(args=args, signal_handler_options=rclpy.signals.SignalHandlerOptions.NO)
    node = None
    try:
        node = EmotionTurtlebot(DeepFace)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.close()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
