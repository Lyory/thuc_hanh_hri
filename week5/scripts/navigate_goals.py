#!/usr/bin/env python3
"""ROS 2 Simple Commander: chạy tuần tự goal, dừng khi lỗi hoặc Ctrl+C."""
import argparse
import csv
import math
from pathlib import Path
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from irobot_create_msgs.action import Undock
from irobot_create_msgs.msg import DockStatus
from lifecycle_msgs.srv import GetState
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data
import yaml

ROOT = Path(__file__).resolve().parents[1]


def pose(node, x, y, yaw):
    msg = PoseStamped()
    msg.header.frame_id = 'map'
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.pose.position.x, msg.pose.position.y = float(x), float(y)
    msg.pose.orientation.z = math.sin(float(yaw) / 2)
    msg.pose.orientation.w = math.cos(float(yaw) / 2)
    return msg


def await_future(node, future, deadline):
    while rclpy.ok() and not future.done():
        if time.monotonic() >= deadline:
            raise TimeoutError('Hết thời gian chờ ROS service/action')
        rclpy.spin_once(node, timeout_sec=0.1)
    if not rclpy.ok():
        raise RuntimeError('ROS đã dừng')
    return future.result()


def wait_ready(node, timeout, initial):
    deadline = time.monotonic() + timeout
    for name in ('amcl', 'bt_navigator'):
        client = node.create_client(GetState, f'{name}/get_state')
        try:
            while time.monotonic() < deadline:
                if client.wait_for_service(timeout_sec=0.5):
                    result = await_future(node, client.call_async(GetState.Request()), deadline)
                    if result.current_state.label == 'active':
                        break
                rclpy.spin_once(node, timeout_sec=0.1)
            else:
                raise TimeoutError(f'{name} chưa active')
        finally:
            node.destroy_client(client)
        if name == 'amcl' and initial is not None:
            node.setInitialPose(pose(node, *initial))
            # Nav2 global costmap cần map -> odom trước khi có thể active.
            next_publish = time.monotonic() + 1
            while not node.initial_pose_received:
                if time.monotonic() >= deadline:
                    raise TimeoutError('AMCL chưa nhận pose. Kiểm tra /scan và /clock.')
                if time.monotonic() >= next_publish:
                    node.setInitialPose(pose(node, *initial))
                    next_publish = time.monotonic() + 1
                rclpy.spin_once(node, timeout_sec=0.1)
    while not node.initial_pose_received or node.get_clock().now().nanoseconds == 0:
        if time.monotonic() >= deadline:
            raise TimeoutError('Chưa có AMCL pose/clock. Đặt 2D Pose Estimate và kiểm tra /scan.')
        rclpy.spin_once(node, timeout_sec=0.1)
    while not node.nav_to_pose_client.wait_for_server(timeout_sec=0.5):
        if time.monotonic() >= deadline:
            raise TimeoutError('/navigate_to_pose chưa sẵn sàng')


def undock(node, timeout):
    status = {'docked': None}
    sub = node.create_subscription(DockStatus, '/dock_status',
                                   lambda msg: status.update(docked=msg.is_docked),
                                   qos_profile_sensor_data)
    client = ActionClient(node, Undock, '/undock')
    deadline = time.monotonic() + timeout
    handle = None
    try:
        while status['docked'] is None:
            if time.monotonic() >= deadline:
                raise TimeoutError('Không nhận được /dock_status')
            rclpy.spin_once(node, timeout_sec=0.1)
        if not status['docked']:
            return
        while not client.wait_for_server(timeout_sec=0.5):
            if time.monotonic() >= deadline:
                raise TimeoutError('/undock chưa sẵn sàng')
        node.info('Tự động undock...')
        handle = await_future(node, client.send_goal_async(Undock.Goal()), deadline)
        if not handle.accepted:
            raise RuntimeError('Undock bị từ chối')
        result = await_future(node, handle.get_result_async(), deadline)
        if result.status != GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError(f'Undock thất bại: {result.status}')
    except BaseException:
        if handle is not None and rclpy.ok():
            await_future(node, handle.cancel_goal_async(), time.monotonic() + 5)
        raise
    finally:
        node.destroy_subscription(sub)
        client.destroy()


def load_goals(path):
    data = yaml.safe_load(Path(path).read_text())
    goals = data['goals']
    if len(goals) < 3:
        raise ValueError('Cần ít nhất 3 goal')
    for goal in goals:
        for key in ('x', 'y', 'yaw'):
            if not math.isfinite(float(goal[key])):
                raise ValueError(f'Tọa độ {key} không hợp lệ')
    if len(data['initial_pose']) != 3 or not all(math.isfinite(float(v)) for v in data['initial_pose']):
        raise ValueError('initial_pose phải có 3 số hữu hạn x,y,yaw')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--goals', default=str(ROOT / 'config/goals.yaml'))
    parser.add_argument('--initialize', action='store_true', help='Đặt pose từ YAML khi vừa reset Gazebo')
    parser.add_argument('--startup-timeout', type=float, default=180)
    parser.add_argument('--goal-timeout', type=float, default=300, help='Giây mô phỏng cho mỗi goal')
    parser.add_argument('--wall-timeout', type=float, default=1800, help='Giới hạn thời gian thực mỗi goal')
    parser.add_argument('--hold', type=float, default=5, help='Dừng để quan sát YOLO, giây mô phỏng')
    parser.add_argument('--log', default=str(ROOT / 'evidence/navigation.csv'))
    args, ros_args = parser.parse_known_args()
    data = load_goals(args.goals)
    rclpy.init(args=ros_args)
    node = BasicNavigator(node_name='week5_navigation')
    node.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
    Path(args.log).parent.mkdir(parents=True, exist_ok=True)
    exit_code = 1
    try:
        node.info('Chờ AMCL và Nav2; pose ban đầu phải khớp LiDAR với tường.')
        wait_ready(node, args.startup_timeout, data['initial_pose'] if args.initialize else None)
        undock(node, args.startup_timeout)
        with open(args.log, 'w', newline='') as output:
            writer = csv.writer(output)
            writer.writerow(['goal', 'x', 'y', 'yaw_rad', 'result', 'sim_seconds', 'wall_seconds'])
            for i, goal in enumerate(data['goals'], 1):
                name = goal.get('name', f'Goal {i}')
                node.info(f'{i}/{len(data["goals"])}: {name} ({goal["x"]}, {goal["y"]}, {goal["yaw"]})')
                start_sim = node.get_clock().now().nanoseconds / 1e9
                start_wall = time.monotonic()
                node.feedback = None  # Không in lại feedback còn lưu từ goal trước.
                if not node.goToPose(pose(node, goal['x'], goal['y'], goal['yaw'])):
                    writer.writerow([name, goal['x'], goal['y'], goal['yaw'], 'REJECTED', 0, 0])
                    output.flush()
                    raise RuntimeError(f'{name} bị từ chối')
                last_log = 0
                timed_out = False
                while not node.isTaskComplete():
                    elapsed = node.get_clock().now().nanoseconds / 1e9 - start_sim
                    if elapsed > args.goal_timeout or time.monotonic() - start_wall > args.wall_timeout:
                        node.cancelTask()
                        timed_out = True
                        break
                    feedback = node.getFeedback()
                    if feedback and time.monotonic() - last_log > 3:
                        node.info(f'{name}: còn {feedback.distance_remaining:.2f} m')
                        last_log = time.monotonic()
                    time.sleep(0.05)
                result = node.getResult()
                label = 'TIMEOUT' if timed_out else result.name
                writer.writerow([name, goal['x'], goal['y'], goal['yaw'], label,
                                 round(node.get_clock().now().nanoseconds / 1e9 - start_sim, 2),
                                 round(time.monotonic() - start_wall, 2)])
                output.flush()
                if timed_out or result != TaskResult.SUCCEEDED:
                    raise RuntimeError(f'{name}: {label}; dừng chuỗi goal')
                node.info(f'{name}: SUCCEEDED')
                hold_until = node.get_clock().now().nanoseconds / 1e9 + args.hold
                hold_deadline = time.monotonic() + args.wall_timeout
                while node.get_clock().now().nanoseconds / 1e9 < hold_until:
                    if time.monotonic() > hold_deadline:
                        raise TimeoutError('/clock dừng trong lúc quan sát')
                    rclpy.spin_once(node, timeout_sec=0.1)
            node.info('HOÀN THÀNH: tất cả goal SUCCEEDED')
            exit_code = 0
    except (KeyboardInterrupt, RuntimeError, TimeoutError) as exc:
        node.error(f'Dừng navigation: {exc}')
    finally:
        if node.result_future is not None and not node.result_future.done() and rclpy.ok():
            node.cancelTask()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
