#!/usr/bin/env python3
"""ROS camera -> cv_bridge -> YOLO -> /yolo/annotated và JSON detections."""
import argparse
import json
from pathlib import Path
import time

import cv2
from cv_bridge import CvBridge
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
import torch
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]


class Detector(Node):
    def __init__(self, args):
        super().__init__('week5_yolo')
        self.args = args
        torch.set_num_threads(2)
        self.bridge = CvBridge()
        self.model = YOLO(args.model)
        self.latest = None
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST)
        self.sub = self.create_subscription(Image, args.topic, self.receive, qos)
        self.images = self.create_publisher(Image, '/yolo/annotated', qos)
        self.detections = self.create_publisher(String, '/yolo/detections', 10)
        Path(args.log).parent.mkdir(parents=True, exist_ok=True)
        self.log = open(args.log, 'a', buffering=1)
        self.last_log = self.last_save = 0
        if args.show:
            cv2.namedWindow('Week 5 - YOLO camera', cv2.WINDOW_NORMAL)
            cv2.resizeWindow('Week 5 - YOLO camera', 580, 435)
            cv2.moveWindow('Week 5 - YOLO camera', args.window_x, args.window_y)
        self.get_logger().info(f'Camera {args.topic}; YOLO {args.model}; device={args.device}')

    def receive(self, message):
        self.latest = message

    def detect(self):
        msg, self.latest = self.latest, None
        if msg is None:
            return
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        result = self.model.predict(frame, conf=self.args.conf, imgsz=self.args.imgsz,
                                    device=self.args.device, verbose=False)[0]
        annotated = result.plot()
        output = self.bridge.cv2_to_imgmsg(annotated, encoding='bgr8')
        output.header = msg.header
        self.images.publish(output)
        objects = []
        for box in result.boxes:
            objects.append({'class': result.names[int(box.cls.item())],
                            'confidence': round(float(box.conf.item()), 3),
                            'bbox_xyxy': [round(v, 1) for v in box.xyxy[0].tolist()]})
        record = {'stamp_sec': msg.header.stamp.sec, 'stamp_nanosec': msg.header.stamp.nanosec,
                  'frame_id': msg.header.frame_id, 'objects': objects}
        encoded = json.dumps(record, ensure_ascii=False)
        self.detections.publish(String(data=encoded))
        now = time.monotonic()
        if now - self.last_log >= 2:
            self.log.write(encoded + '\n')
            self.get_logger().info(' | '.join(f'{o["class"]}: {o["confidence"]:.0%}' for o in objects)
                                   or 'Không phát hiện vật thể trong frame hiện tại')
            self.last_log = now
        if objects and now - self.last_save >= 10:
            cv2.imwrite(str(Path(self.args.log).parent / 'yolo_latest.jpg'), annotated)
            self.last_save = now
        if self.args.show:
            cv2.imshow('Week 5 - YOLO camera', annotated)
            if cv2.waitKey(1) & 0xff == ord('q'):
                raise KeyboardInterrupt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--topic', default='/oakd/rgb/preview/image_raw')
    parser.add_argument('--model', default=str(ROOT / 'weights/yolov8n.pt'))
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--conf', type=float, default=0.35)
    parser.add_argument('--imgsz', type=int, default=640)
    parser.add_argument('--fps', type=float, default=3)
    parser.add_argument('--show', action='store_true')
    parser.add_argument('--window-x', type=int, default=1210)
    parser.add_argument('--window-y', type=int, default=80)
    parser.add_argument('--log', default=str(ROOT / 'evidence/detections.jsonl'))
    args, ros_args = parser.parse_known_args()
    if args.fps <= 0 or not 0 <= args.conf <= 1:
        parser.error('fps phải > 0 và conf nằm trong [0,1]')
    if not Path(args.model).is_file():
        parser.error('Chưa có weights. Chạy bash scripts/install.sh hoặc truyền --model.')
    rclpy.init(args=ros_args)
    node = Detector(args)
    last_run = 0
    last_warning = time.monotonic()
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.02)
            now = time.monotonic()
            if now - last_run >= 1 / args.fps and node.latest is not None:
                node.detect()
                last_run = time.monotonic()
                last_warning = last_run
            elif now - last_warning > 10:
                node.get_logger().warning('Chưa nhận ảnh RGB; kiểm tra topic, bridge và Gazebo Play.')
                last_warning = now
    except KeyboardInterrupt:
        pass
    finally:
        node.log.close()
        node.destroy_node()
        cv2.destroyAllWindows()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
