"""Verify busy-command protection and cancellation against the real Nav2 server."""
import json
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

ROOT = Path(__file__).resolve().parents[1]
rclpy.init()
node = Node('verify_voice_controls')
events = []
node.create_subscription(String, '/voice_navigation/status', lambda m: events.append(json.loads(m.data)), 100)
pub = node.create_publisher(String, '/voice_command', 10)


def wait(predicate, timeout=20.):
    deadline = time.monotonic()+timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise TimeoutError(events)
        rclpy.spin_once(node, timeout_sec=.1)


try:
    wait(lambda: pub.get_subscription_count() > 0)
    # Discover the return status channel too before testing fast transitions.
    deadline = time.monotonic()+15.
    while not any(e['state'] == 'INVALID' for e in events):
        if time.monotonic() > deadline:
            raise TimeoutError('Status channel not discovered')
        pub.publish(String(data='kiểm tra kết nối'))
        until = time.monotonic()+.5
        while time.monotonic() < until:
            rclpy.spin_once(node, timeout_sec=.1)
    events.clear()
    pub.publish(String(data='Đi từ hành lang đến phòng học'))
    wait(lambda: any(e['state'] == 'GOAL_SENT' for e in events))
    pub.publish(String(data='Đi đến phòng thí nghiệm'))
    wait(lambda: any(e['state'] == 'BUSY' for e in events))
    pub.publish(String(data='dừng lại'))
    wait(lambda: any(e['state'] == 'CANCELED' for e in events), 40.)
    assert len([e for e in events if e['state'] == 'GOAL_SENT']) == 1, events
    (ROOT/'evidence/control_verification.json').write_text(json.dumps(events, ensure_ascii=False, indent=2)+'\n')
    print('PASS: busy command rejected, current goal canceled, remaining waypoint not sent')
finally:
    pub.publish(String(data='dừng lại'))
    rclpy.spin_once(node, timeout_sec=.2)
    node.destroy_node()
    rclpy.shutdown()
