#!/usr/bin/env python3
"""Ghi ít nhất 3 Publish Point từ RViz thành YAML; yaw truyền bằng radian."""
import argparse
from pathlib import Path

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PointStamped
import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='config/goals_recorded.yaml')
    parser.add_argument('--yaw', type=float, nargs='+', default=[0., 0., 0.])
    args = parser.parse_args()
    if len(args.yaw) < 3:
        parser.error('Cần ít nhất 3 giá trị yaw')
    rclpy.init()
    node = Node('week5_record_goals')
    goals = []

    def clicked(msg):
        if msg.header.frame_id != 'map':
            node.get_logger().error('RViz Fixed Frame phải là map')
            return
        if len(goals) >= len(args.yaw):
            return
        goals.append({'name': f'Goal {len(goals)+1}', 'x': round(msg.point.x, 3),
                      'y': round(msg.point.y, 3), 'yaw': args.yaw[len(goals)]})
        node.get_logger().info(str(goals[-1]))

    node.create_subscription(PointStamped, '/clicked_point', clicked, 10)
    node.get_logger().info(f'Dùng Publish Point chọn {len(args.yaw)} điểm trống trên map.')
    try:
        while rclpy.ok() and len(goals) < len(args.yaw):
            rclpy.spin_once(node, timeout_sec=0.2)
        if len(goals) == len(args.yaw):
            target = Path(args.output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(yaml.safe_dump({'initial_pose': [0., 0., 0.], 'goals': goals}, sort_keys=False))
            node.get_logger().info(f'Đã lưu {target}; initial_pose cần kiểm tra theo robot thực tế.')
    except KeyboardInterrupt:
        node.get_logger().info('Dừng ghi tọa độ; chưa lưu file nếu thiếu goal.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
