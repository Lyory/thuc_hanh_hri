"""ROS adapter: gesture events, odometry progress, lidar guard, velocity watchdog."""
import math
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from .behavior import Behavior


class RobotBehaviorNode(Node):
    def __init__(self):
        super().__init__('robot_behavior_node')
        defaults = {
            'stable_time': 0.45, 'signal_timeout': 0.8, 'selection_timeout': 8.0,
            'linear_speed': 0.12, 'angular_speed': 0.45, 'leg_distance': 0.35,
            'circle_radius': 0.45, 'sensor_timeout': 0.6, 'stop_distance': 0.40,
        }
        for key, value in defaults.items():
            self.declare_parameter(key, value)
        params = {key: self.get_parameter(key).value for key in defaults}
        if not all(math.isfinite(value) and value > 0 for value in params.values()):
            raise ValueError('All behavior parameters must be finite and positive')
        self.sensor_timeout = params.pop('sensor_timeout')
        self.stop_distance = params.pop('stop_distance')
        if (params['linear_speed'] > 0.25 or params['angular_speed'] > 1.0
                or params['linear_speed'] / params['circle_radius'] > 1.0
                or self.stop_distance < 0.30):
            raise ValueError('Use speed <= 0.25 m/s, turn <= 1 rad/s, clearance >= 0.30 m')
        self.behavior = Behavior(**params)
        self.last_odom = self.last_scan = float('-inf')
        self.odom_stamp = self.scan_stamp = None
        self.previous_pose = None
        self.scan_safe = False
        self.last_status = None
        self.velocity = self.create_publisher(Twist, '/cmd_vel', 1)
        self.status = self.create_publisher(String, '/robot_behavior_state', 1)
        # Depth one avoids replaying a queue of old control commands.
        control_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(String, '/detected_gesture', self.on_gesture, control_qos)
        self.create_subscription(Odometry, '/odom', self.on_odom, qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.timer = self.create_timer(0.05, self.control_tick,
                                      clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.get_logger().info('Ready. Select Wave / Pointing_Up / Victory, then Thumb_Up.')

    def on_gesture(self, message):
        self.behavior.ingest(message.data, time.monotonic())
        # Stop in the subscription callback; do not wait for the next control tick.
        if self.behavior.state != 'RUNNING':
            self.publish_velocity()

    def on_odom(self, message):
        stamp = (message.header.stamp.sec, message.header.stamp.nanosec)
        if stamp == self.odom_stamp:
            return
        p, q = message.pose.pose.position, message.pose.pose.orientation
        values = (p.x, p.y, q.x, q.y, q.z, q.w)
        if not all(math.isfinite(v) for v in values):
            return
        norm = q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w
        if abs(norm - 1.0) > 0.05:
            return
        yaw = math.atan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        if self.previous_pose is not None:
            x0, y0, yaw0 = self.previous_pose
            dx, dy = p.x - x0, p.y - y0
            turn = math.atan2(math.sin(yaw-yaw0), math.cos(yaw-yaw0))
            if math.hypot(dx, dy) > 0.25 or abs(turn) > 0.5:
                self.behavior.stop('Odometry jumped: select again')
                self.publish_velocity()
            else:
                signed_distance = dx*math.cos(yaw0) + dy*math.sin(yaw0)
                self.behavior.add_odometry(signed_distance, turn)
        self.previous_pose = (p.x, p.y, yaw)
        self.last_odom, self.odom_stamp = time.monotonic(), stamp

    def on_scan(self, message):
        stamp = (message.header.stamp.sec, message.header.stamp.nanosec)
        if stamp == self.scan_stamp:
            return
        # All-around clearance covers reverse, turning and the full circular path.
        # +inf is a valid no-return; zero, NaN and -inf are invalid.
        usable = [r for r in message.ranges if r == math.inf or
                  (math.isfinite(r) and 0 < r <= message.range_max)]
        self.scan_safe = bool(
            message.ranges and 0 <= message.range_min < self.stop_distance
            and len(usable) >= 0.8 * len(message.ranges)
            and min(usable, default=0.0) >= self.stop_distance)
        self.last_scan, self.scan_stamp = time.monotonic(), stamp
        if not self.scan_safe and self.behavior.state == 'RUNNING':
            self.behavior.stop('Obstacle too close or invalid lidar')
            self.publish_velocity()

    def publish_velocity(self, linear=0.0, angular=0.0):
        msg = Twist()
        msg.linear.x, msg.angular.z = float(linear), float(angular)
        self.velocity.publish(msg)

    def control_tick(self):
        now = time.monotonic()
        linear, angular = self.behavior.tick(now)
        if self.behavior.state == 'RUNNING':
            if now - self.last_odom > self.sensor_timeout:
                self.behavior.stop('Odometry missing or stale')
            elif now - self.last_scan > self.sensor_timeout:
                self.behavior.stop('Lidar missing or stale')
            elif not self.scan_safe:
                self.behavior.stop('Obstacle too close or invalid lidar')
        if self.behavior.state != 'RUNNING':
            linear, angular = 0.0, 0.0
        self.publish_velocity(linear, angular)
        status = f'{self.behavior.state}|{self.behavior.reason}'
        self.status.publish(String(data=status))
        if status != self.last_status:
            self.get_logger().info(status)
            self.last_status = status


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = RobotBehaviorNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node:
            if rclpy.ok():
                node.publish_velocity()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
