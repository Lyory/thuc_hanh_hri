"""Verify A → C → B, the full Nav2 preview, and atomic rejection of unknown regions."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from nav_msgs.msg import Path as NavPath
from std_msgs.msg import String
from commands import parse_command
from map_utils import GridMap

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--speech', action='store_true', help='Use existing synthetic speech command_6.mp3 through Whisper')
    args = parser.parse_args()
    rclpy.init()
    node = Node('verify_multidest')
    events, previews, heard = [], [], []
    invalid = 'Đi từ phòng A qua phòng D rồi đến phòng B.'
    qos = QoSProfile(depth=100, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(String, '/voice_navigation/status', lambda m:events.append(json.loads(m.data)), qos)
    node.create_subscription(NavPath, '/voice_navigation/preview_path', lambda m:previews.append(m), qos)
    node.create_subscription(String, '/voice_command', lambda m:heard.append(m.data) if m.data != invalid else None, 10)
    pub = node.create_publisher(String, '/voice_command', 10)
    process = None

    def wait(predicate, timeout):
        deadline = time.monotonic()+timeout
        while not predicate():
            if time.monotonic() > deadline:
                raise TimeoutError(events[-5:])
            rclpy.spin_once(node, timeout_sec=.1)

    try:
        wait(lambda:pub.get_subscription_count() >= 2 and events, 20.)
        events.clear()
        deadline = time.monotonic()+15.
        while not any(e['state']=='INVALID' and e['command']==invalid for e in events):
            if time.monotonic()>deadline:
                raise TimeoutError('Status channel not discovered')
            pub.publish(String(data=invalid))
            until=time.monotonic()+.5
            while time.monotonic()<until:
                rclpy.spin_once(node,timeout_sec=.1)
        assert not any(e['state'] in ('PLANNING','GOAL_SENT') for e in events)
        events.clear(); previews.clear(); heard.clear()
        text = 'Đi từ phòng A qua hành lang C rồi đến phòng B.'
        route = ['A','C','B']
        begin = time.monotonic()
        if args.speech:
            audio = ROOT/'evidence/synthetic_speech/command_6.mp3'
            assert audio.is_file(), 'Tạo mẫu bằng scripts/make_speech_fixtures.py trước'
            with (ROOT/'evidence/multidest_asr.log').open('w') as log:
                process = subprocess.Popen([sys.executable,str(ROOT/'scripts/speech_recognition.py'),
                                            '--audio',str(audio)],stdout=log,stderr=subprocess.STDOUT)
                wait(lambda:process.poll() is not None, 120.)
                assert process.returncode == 0
        else:
            pub.publish(String(data=text))
        wait(lambda:bool(heard), 10.)
        regions = json.loads((ROOT/'config/regions.json').read_text())['regions']
        assert parse_command(heard[-1],regions) == route, heard
        wait(lambda:any(e['state'] in ('COMPLETED','FAILED','INVALID','NOT_READY') and e.get('command')!=invalid and e.get('route')==route for e in events), 360.)
        events[:]=[e for e in events if e.get('command')!=invalid and e.get('route')==route]
        assert events[-1]['state'] == 'COMPLETED', events[-5:]
        assert any(e['state']=='PLAN_READY' for e in events)
        plan_index = next(i for i,e in enumerate(events) if e['state']=='PLAN_READY')
        assert plan_index < next(i for i,e in enumerate(events) if e['state']=='GOAL_SENT')
        goals = [e for e in events if e['state']=='GOAL_RESULT']
        assert [e['region'] for e in goals] == route and all(e['action_status']==4 for e in goals)
        assert [e['step'] for e in goals] == [1,2,3]
        assert events[-1]['completed'] == route
        path = next(p for p in previews if p.poses)
        points = [(p.pose.position.x,p.pose.position.y) for p in path.poses]
        grid = GridMap(ROOT/'maps/map.yaml')
        assert path.header.frame_id == 'map' and all(grid.free[grid.pixel(x,y)] for x,y in points)
        cursor = 0
        for region in route:
            goal = next(r['goal'] for r in regions if r['id']==region)
            distances = [math.dist(p,(goal['x'],goal['y'])) for p in points[cursor:]]
            nearest = min(range(len(distances)),key=distances.__getitem__)
            assert distances[nearest] < .15, (region,distances[nearest])
            cursor += nearest+1
        wait(lambda:bool(previews) and not previews[-1].poses, 5.)
        result = {'recognized':heard[-1], 'route':route, 'result':'PASS',
                  'source':'synthetic speech through Whisper' if args.speech else 'text',
                  'wall_seconds':round(time.monotonic()-begin,2), 'preview_points':len(points),
                  'preview_visits_in_order':True, 'preview_on_free_cells':True, 'preview_cleared_on_completion':True,
                  'max_recoveries':max(e.get('recoveries',0) for e in events),
                  'goal_results':[{'region':e['region'],'step':e['step'],'status':e['action_status']} for e in goals],
                  'unknown_middle_region':'rejected before planning or motion'}
        filename = 'multidest_speech_verification.json' if args.speech else 'multidest_verification.json'
        (ROOT/'evidence'/filename).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False),flush=True)
    finally:
        if process and process.poll() is None:
            process.kill(); process.wait()
        pub.publish(String(data='Dừng lại'))
        rclpy.spin_once(node,timeout_sec=.2)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
