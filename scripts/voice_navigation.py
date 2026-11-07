"""Sequential, nonblocking NavigateToPose client for Vietnamese commands."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import rclpy
from rclpy.action import ActionClient
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from action_msgs.msg import GoalStatus
from nav2_msgs.action import NavigateToPose, ComputePathThroughPoses
from nav_msgs.msg import Path as NavPath
from std_msgs.msg import String
from visualization_msgs.msg import Marker, MarkerArray
from geometry_msgs.msg import Point, PoseStamped
import numpy as np
from commands import parse_command
from map_utils import GridMap

ROOT = Path(__file__).resolve().parents[1]


class VoiceNavigator(Node):
    def __init__(self, filename, map_path):
        super().__init__('voice_navigation')
        self.set_parameters([rclpy.parameter.Parameter('use_sim_time', value=True)])
        doc = json.loads(Path(filename).read_text())
        grid = GridMap(map_path)
        if (hashlib.sha256(grid.image.tobytes()).hexdigest() != doc['image_sha256']
                or grid.meta != doc['map_metadata']):
            raise ValueError('Map thay đổi: chạy lại segment_map.py trước')
        self.regions = {r['id']: r for r in doc['regions']}
        for region in self.regions.values():
            goal = region['goal']
            if grid.clearance[grid.pixel(goal['x'], goal['y'])] < doc['clearance']:
                raise ValueError('Goal không đủ khoảng trống')
        self.client = ActionClient(self, NavigateToPose, '/navigate_to_pose')
        self.planner = ActionClient(self, ComputePathThroughPoses, '/compute_path_through_poses')
        status_qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.pub = self.create_publisher(String, '/voice_navigation/status', status_qos)
        self.sub = self.create_subscription(String, '/voice_command', self.command, 10)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.markers = self.create_publisher(MarkerArray, '/semantic_regions', qos)
        self.preview = self.create_publisher(NavPath, '/voice_navigation/preview_path', qos)
        self.labels = np.load(ROOT/'config/region_labels.npy')
        self.grid = grid
        self.timer = self.create_timer(3., self.show_regions)
        self.queue = []
        self.busy = False
        self.goal_handle = None
        self.cancel_requested = False
        self.log = ROOT / 'evidence/navigation.jsonl'
        self.log.parent.mkdir(exist_ok=True)
        self.last_command = ''
        self.current_route = []
        self.completed_route = []
        self.step = 0
        self.plan_generation = 0
        self.planning = False
        self.plan_handle = None
        self.plan_deadline = 0.
        self.plan_timer = self.create_timer(.5, self.check_plan, clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.last_feedback = 0.
        self.status('READY', reason='Node nhận lệnh đã mở; hãy initialize để kích hoạt robot.')
        self.show_regions()
        self.clear_preview()

    def status(self, state, **details):
        event = {'time': time.time(), 'state': state, 'command': self.last_command,
                 'route': self.current_route, 'completed': list(self.completed_route),
                 'step': self.step, **details}
        payload = json.dumps(event, ensure_ascii=False)
        self.pub.publish(String(data=payload))
        self.get_logger().info(payload)
        with self.log.open('a') as stream:
            stream.write(payload+'\n')

    def command(self, msg):
        self.last_command = msg.data
        try:
            route = parse_command(msg.data, list(self.regions.values()))
        except ValueError as error:
            self.status('INVALID', command=msg.data, reason=str(error))
            return
        if not route:
            self.queue.clear()
            self.cancel_requested = True
            self.clear_preview()
            if self.planning:
                self.stop_planning()
                self.busy = False
                self.status('CANCELED')
            elif self.goal_handle:
                self.goal_handle.cancel_goal_async().add_done_callback(self.canceled)
            else:
                self.status('CANCEL_REQUESTED' if self.busy else 'IDLE')
            return
        if self.busy:
            self.status('BUSY', reason='Đợi hoàn tất hoặc nói dừng lại trước khi nhận lệnh mới')
            return
        if not self.client.server_is_ready() or not self.planner.server_is_ready():
            self.status('NOT_READY', reason='Nav2 chưa sẵn sàng')
            return
        self.current_route = list(route)
        self.completed_route = []
        self.step = 0
        self.queue = route
        self.cancel_requested = False
        self.busy = True
        self.status('ACCEPTED', command=msg.data, route=route)
        self.plan_route()

    def target_pose(self, region):
        target = self.regions[region]['goal']
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(target['x'])
        pose.pose.position.y = float(target['y'])
        pose.pose.orientation.z = math.sin(target['yaw']/2)
        pose.pose.orientation.w = math.cos(target['yaw']/2)
        return pose

    def clear_preview(self):
        path = NavPath()
        path.header.frame_id = 'map'
        self.preview.publish(path)

    def plan_route(self):
        self.clear_preview()
        self.plan_generation += 1
        generation = self.plan_generation
        self.planning = True
        self.plan_deadline = time.monotonic()+15.
        self.status('PLANNING')
        goal = ComputePathThroughPoses.Goal()
        goal.goals = [self.target_pose(region) for region in self.current_route]
        goal.planner_id = 'GridBased'
        goal.use_start = False
        try:
            self.planner.send_goal_async(goal).add_done_callback(lambda f: self.plan_response(f, generation))
        except Exception as error:
            self.fail(str(error))

    def plan_response(self, future, generation):
        try:
            handle = future.result()
            if generation != self.plan_generation:
                if handle.accepted:
                    handle.cancel_goal_async()
                return
            if not handle.accepted:
                self.fail('Nav2 từ chối lập đường toàn tuyến')
                return
            self.plan_handle = handle
            handle.get_result_async().add_done_callback(lambda f: self.plan_result(f, generation))
        except Exception as error:
            if generation == self.plan_generation:
                self.fail(str(error))

    def plan_result(self, future, generation):
        if generation != self.plan_generation:
            return
        try:
            result = future.result()
            self.planning = False
            self.plan_handle = None
            if result.status != GoalStatus.STATUS_SUCCEEDED or not result.result.path.poses:
                self.fail('Không lập được đường đi qua tất cả khu vực; chưa gửi goal di chuyển')
                return
            self.preview.publish(result.result.path)
            self.status('PLAN_READY', preview_points=len(result.result.path.poses))
            self.send_next()
        except Exception as error:
            self.fail(str(error))

    def stop_planning(self):
        self.plan_generation += 1
        self.planning = False
        if self.plan_handle:
            self.plan_handle.cancel_goal_async()
            self.plan_handle = None

    def check_plan(self):
        if self.planning and time.monotonic() >= self.plan_deadline:
            self.fail('Hết thời gian lập đường toàn tuyến; chưa gửi goal di chuyển')

    def canceled(self, future):
        try:
            response = future.result()
            self.status('CANCEL_ACK' if response.goals_canceling else 'CANCEL_REJECTED')
        except Exception as error:
            self.status('CANCEL_ERROR', reason=str(error))

    def fail(self, reason):
        self.stop_planning()
        self.clear_preview()
        self.queue.clear()
        self.goal_handle = None
        self.busy = False
        self.status('FAILED', reason=reason)

    def send_next(self):
        if not self.queue or self.cancel_requested:
            self.busy = False
            self.clear_preview()
            self.status('CANCELED' if self.cancel_requested else 'COMPLETED')
            return
        self.current = self.queue.pop(0)
        self.step = len(self.current_route)-len(self.queue)
        target = self.regions[self.current]['goal']
        goal = NavigateToPose.Goal()
        goal.pose = self.target_pose(self.current)
        self.status('GOAL_SENT', region=self.current, goal=target)
        self.last_feedback = 0.
        try:
            self.client.send_goal_async(goal, feedback_callback=lambda m, region=self.current: self.feedback(m, region)).add_done_callback(self.goal_response)
        except Exception as error:
            self.fail(str(error))

    def feedback(self, message, region):
        if not self.busy or region != self.current or time.monotonic()-self.last_feedback < 2.:
            return
        self.last_feedback = time.monotonic()
        feedback = message.feedback
        self.status('PROGRESS', region=self.current, distance_remaining=round(feedback.distance_remaining, 2),
                    recoveries=feedback.number_of_recoveries)

    def goal_response(self, future):
        try:
            self.goal_handle = future.result()
            if not self.goal_handle.accepted:
                self.fail('Nav2 từ chối goal')
                return
            self.goal_handle.get_result_async().add_done_callback(self.result)
            if self.cancel_requested:
                self.goal_handle.cancel_goal_async().add_done_callback(self.canceled)
        except Exception as error:
            self.fail(str(error))

    def result(self, future):
        try:
            status = future.result().status
            self.goal_handle = None
            if status == GoalStatus.STATUS_SUCCEEDED:
                self.completed_route.append(self.current)
            self.status('GOAL_RESULT', region=self.current, action_status=status)
            if status == GoalStatus.STATUS_SUCCEEDED:
                self.send_next()
            elif status == GoalStatus.STATUS_CANCELED:
                self.queue.clear()
                self.busy = False
                self.clear_preview()
                self.status('CANCELED')
            else:
                self.fail(f'Nav2 kết thúc với status {status}; hủy các đích còn lại')
        except Exception as error:
            self.fail(str(error))

    def show_regions(self):
        if hasattr(self, "marker_array"):
            self.markers.publish(self.marker_array)
            return
        array = MarkerArray()
        for i, region in enumerate(self.regions.values()):
            marker = Marker()
            marker.header.frame_id = 'map'
            marker.ns = 'semantic_regions'
            marker.id = i
            marker.type = Marker.TEXT_VIEW_FACING
            marker.action = Marker.ADD
            marker.pose.position.x = region['goal']['x']
            marker.pose.position.y = region['goal']['y']
            marker.pose.position.z = .5
            marker.pose.orientation.w = 1.
            marker.scale.z = .28
            marker.color.r = marker.color.g = marker.color.b = marker.color.a = 1.
            marker.text = region['id']
            array.markers.append(marker)
            fill = Marker()
            fill.header.frame_id = 'map'
            fill.ns = 'region_fill'
            fill.id = i
            fill.type = Marker.CUBE_LIST
            fill.action = Marker.ADD
            fill.pose.orientation.w = 1.
            fill.scale.x = fill.scale.y = self.grid.res*2
            fill.scale.z = .015
            colors = ((.35,.8,.55),(.3,.6,1.),(1.,.75,.25))
            fill.color.r,fill.color.g,fill.color.b = colors[i%3]
            fill.color.a = .2
            for r,c in np.argwhere(self.labels[::2,::2] == i+1):
                x,y = self.grid.world(int(r)*2,int(c)*2)
                fill.points.append(Point(x=float(x),y=float(y),z=.025))
            array.markers.append(fill)
        self.marker_array = array
        self.markers.publish(array)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--regions', default=str(ROOT/'config/regions.json'))
    p.add_argument('--map', default=str(ROOT/'maps/map.yaml'))
    args, ros_args = p.parse_known_args()
    rclpy.init(args=ros_args)
    node = VoiceNavigator(args.regions, args.map)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.stop_planning()
        node.clear_preview()
        node.cancel_requested = True
        node.queue.clear()
        if node.goal_handle:
            future = node.goal_handle.cancel_goal_async()
            rclpy.spin_until_future_complete(node, future, timeout_sec=2.)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
