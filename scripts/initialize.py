#!/usr/bin/env python3
"""Khởi tạo AMCL và undock trong mô phỏng mới; có timeout."""
import argparse
import json
from pathlib import Path
import math
import time

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from irobot_create_msgs.action import Undock
from irobot_create_msgs.msg import DockStatus
from lifecycle_msgs.srv import GetState
from nav2_simple_commander.robot_navigator import BasicNavigator
from rclpy.action import ActionClient
from rclpy.qos import qos_profile_sensor_data

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
        node.info(f'Chờ {name} active...')
        client = node.create_client(GetState, f'{name}/get_state')
        try:
            while time.monotonic() < deadline:
                if client.wait_for_service(timeout_sec=0.5):
                    future = client.call_async(GetState.Request())
                    try:
                        # A lost lifecycle response must not consume the entire
                        # startup timeout and prevent the initial pose being sent.
                        result = await_future(node, future, min(deadline, time.monotonic() + 3.))
                    except TimeoutError:
                        client.remove_pending_request(future)
                        future.cancel()
                        node.warn(f'{name}/get_state chưa phản hồi; thử lại...')
                        continue
                    if result.current_state.label == 'active':
                        break
                    # Clock callbacks can make spin_once return immediately;
                    # do not flood an inactive lifecycle node with requests.
                    time.sleep(.2)
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



def main():
    p = argparse.ArgumentParser()
    p.add_argument('--timeout', type=float, default=240.)
    a = p.parse_args()
    if not math.isfinite(a.timeout) or a.timeout <= 0:
        p.error('--timeout phải là số dương hữu hạn')
    state_file = Path(__file__).resolve().parents[1]/'.docker-runtime/initialization.json'
    state_file.parent.mkdir(exist_ok=True)
    def write_state(state, **details):
        temporary = state_file.with_suffix('.tmp')
        temporary.write_text(json.dumps({'state': state, 'time': time.time(), **details}))
        temporary.replace(state_file)
    write_state('INITIALIZING')
    rclpy.init()
    node = BasicNavigator(node_name='week7_initialize')
    node.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
    try:
        wait_ready(node, a.timeout, [0., 0., 0.])
        undock(node, a.timeout)
        write_state('READY')
        print('READY: AMCL active, Nav2 active, robot undocked', flush=True)
    except BaseException as error:
        write_state('ERROR', message=str(error))
        raise
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
