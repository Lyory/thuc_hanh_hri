"""Run after initialize.py. Verify text-to-action chain against real Nav2."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--speech', action='store_true', help='Publish commands from Whisper on synthetic audio')
    parser.add_argument('--output', help='Đường dẫn JSON kết quả, tính từ root project')
    args = parser.parse_args()
    rclpy.init()
    node = Node('week7_verify')
    events = []
    node.create_subscription(String, '/voice_navigation/status', lambda m: events.append(json.loads(m.data)), 100)
    pub = node.create_publisher(String, '/voice_command', 10)

    def wait(predicate, timeout):
        until = time.monotonic()+timeout
        while not predicate():
            if time.monotonic() > until:
                raise TimeoutError('Không nhận được kết quả mong đợi')
            rclpy.spin_once(node, timeout_sec=.1)

    records = []
    try:
        wait(lambda: pub.get_subscription_count() > 0, 20.)
        deadline = time.monotonic()+15.
        while not any(e['state'] == 'INVALID' for e in events):
            if time.monotonic() > deadline:
                raise TimeoutError('Status channel not discovered')
            pub.publish(String(data='kiểm tra kết nối'))
            until = time.monotonic()+.5
            while time.monotonic() < until:
                rclpy.spin_once(node, timeout_sec=.1)
        commands = [('Đi đến khu vực A.', ['A']),
                    ('Di chuyển từ khu vực A đến khu vực B.', ['A','B']),
                    ('Đi đến phòng thí nghiệm.' if args.speech else 'Đi đến hành lang.',
                     ['B'] if args.speech else ['C'])]
        if not args.speech:
            # After reaching C, verify A is visited before B from another area.
            commands.append(('Đi từ khu vực A đến khu vực B.', ['A', 'B']))

        def send(text, index):
            if args.speech:
                with (ROOT/'evidence/speech_pipeline.log').open('a') as log:
                    subprocess.run([sys.executable, str(ROOT/'scripts/speech_recognition.py'),
                                    '--audio', str(ROOT/f'evidence/synthetic_speech/command_{index}.mp3')],
                                   check=True, stdout=log, stderr=subprocess.STDOUT, timeout=120.)
            else:
                pub.publish(String(data=text))

        for index, (text, route) in enumerate(commands, 1):
            events.clear()
            begin = time.monotonic()
            send(text, index)
            wait(lambda: any(e['state'] in ('COMPLETED','FAILED','INVALID','NOT_READY') for e in events), 900.)
            assert events[-1]['state'] == 'COMPLETED', events
            results = [e for e in events if e['state'] == 'GOAL_RESULT']
            assert [e['region'] for e in results] == route, results
            assert all(e['action_status'] == 4 for e in results), results
            record = {'command': text, 'route': route, 'wall_seconds': round(time.monotonic()-begin,2), 'result': 'PASS'}
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
        events.clear()
        send('Đi từ khu vực A đến khu vực D.', 4)
        wait(lambda: any(e['state'] == 'INVALID' for e in events), 10.)
        assert not any(e['state'] == 'GOAL_SENT' for e in events)
        records.append({'command': 'Đi đến khu vực D.' if args.speech else 'Đi từ khu vực A đến khu vực D.',
                        'result': 'INVALID; no goal sent'})
        filename = 'speech_nav2_verification.json' if args.speech else 'nav2_verification.json'
        output = ROOT/args.output if args.output else ROOT/'evidence'/filename
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
        print('PASS: real Nav2 sequences; unknown region rejected', flush=True)
    finally:
        pub.publish(String(data='dừng lại'))
        rclpy.spin_once(node, timeout_sec=.5)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
