#!/usr/bin/env python3
"""Ghi telemetry và hazard khi kiểm thử; không gửi lệnh cho robot."""
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from rclpy.time import Time
from geometry_msgs.msg import PoseWithCovarianceStamped
from irobot_create_msgs.msg import HazardDetection, HazardDetectionVector
from nav_msgs.msg import OccupancyGrid, Odometry
from sensor_msgs.msg import LaserScan
from tf2_ros import Buffer, TransformListener, TransformException

ROOT = Path(__file__).resolve().parents[1]


class Monitor(Node):
    def __init__(self):
        super().__init__('week5_monitor')
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
        self.tf = Buffer()
        self.listener = TransformListener(self.tf, self)
        self.map = self.distance = None
        self.last_scan = 0
        self.stats = {'hazard_messages': 0, 'bump_messages': 0, 'stall_messages': 0,
                      'scan_alignment_samples': [], 'last_amcl': None, 'last_ground_truth': None}
        self.file = open(ROOT / 'evidence/telemetry.jsonl', 'w', buffering=1)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(OccupancyGrid, '/map', self.on_map, qos)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose',
                                 lambda m: self.on_pose('last_amcl', m.pose.pose), qos)
        self.create_subscription(Odometry, '/sim_ground_truth_pose',
                                 lambda m: self.on_pose('last_ground_truth', m.pose.pose), qos_profile_sensor_data)
        self.create_subscription(HazardDetectionVector, '/hazard_detection', self.on_hazards, qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.create_timer(2., self.save)

    def on_map(self, msg):
        self.map = msg
        cells = np.array(msg.data).reshape((msg.info.height, msg.info.width))
        self.distance = cv2.distanceTransform((cells < 65).astype(np.uint8), cv2.DIST_L2, 5) * msg.info.resolution

    def on_pose(self, key, pose):
        q = pose.orientation
        self.stats[key] = {'x': pose.position.x, 'y': pose.position.y,
                           'yaw': math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))}

    def on_hazards(self, msg):
        self.stats['hazard_messages'] += 1
        types = [d.type for d in msg.detections]
        if HazardDetection.BUMP in types:
            self.stats['bump_messages'] += 1
        if HazardDetection.STALL in types:
            self.stats['stall_messages'] += 1
        if HazardDetection.BUMP in types or HazardDetection.STALL in types:
            self.file.write(json.dumps({'sim_sec': self.get_clock().now().nanoseconds/1e9, 'hazards': types})+'\n')

    def on_scan(self, msg):
        if self.map is None or time.monotonic() - self.last_scan < 2:
            return
        self.last_scan = time.monotonic()
        try:
            t = self.tf.lookup_transform('map', msg.header.frame_id,
                                         Time.from_msg(msg.header.stamp)).transform
        except TransformException:
            return
        q = t.rotation
        yaw = math.atan2(2*(q.w*q.z+q.x*q.y), 1-2*(q.y*q.y+q.z*q.z))
        m = self.map.info
        # Map gốc có origin yaw=0. Chỉ so endpoint hữu hạn, trong map.
        distances = []
        for i in range(0, len(msg.ranges), 4):
            r = msg.ranges[i]
            if not math.isfinite(r) or not msg.range_min < r < msg.range_max:
                continue
            a = yaw + msg.angle_min + i*msg.angle_increment
            x = int((t.translation.x + r*math.cos(a)-m.origin.position.x)/m.resolution)
            y = int((t.translation.y + r*math.sin(a)-m.origin.position.y)/m.resolution)
            if 0 <= x < m.width and 0 <= y < m.height:
                distances.append(float(self.distance[y, x]))
        if distances:
            self.stats['scan_alignment_samples'].append({
                'sim_sec': self.get_clock().now().nanoseconds/1e9,
                'fraction_within_15cm': sum(d < .15 for d in distances)/len(distances),
                'median_distance_m': float(np.median(distances)), 'endpoints': len(distances)})

    def save(self):
        (ROOT / 'evidence/monitor-summary.json').write_text(json.dumps(self.stats, indent=2))
        self.file.write(json.dumps({'sim_sec': self.get_clock().now().nanoseconds/1e9,
                                   'amcl': self.stats['last_amcl'], 'ground_truth': self.stats['last_ground_truth']})+'\n')


def main():
    rclpy.init()
    node = Monitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.save()
        node.file.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
