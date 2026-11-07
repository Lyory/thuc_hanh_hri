"""Check that failed/canceled preview requests cannot start robot motion."""
from concurrent.futures import Future
import json
from pathlib import Path
from types import SimpleNamespace as S
import time
import unittest
from unittest.mock import Mock

from action_msgs.msg import GoalStatus
from std_msgs.msg import String
from voice_navigation import VoiceNavigator


def future(value):
    result = Future()
    result.set_result(value)
    return result


class PlanningTests(unittest.TestCase):
    def node(self):
        return S(plan_generation=1, planning=True, plan_handle=None,
                 preview=S(publish=Mock()), status=Mock(), fail=Mock(), send_next=Mock())

    def result(self, status=GoalStatus.STATUS_SUCCEEDED, poses=None):
        return future(S(status=status, result=S(path=S(poses=[object()] if poses is None else poses))))

    def test_success_publishes_preview_before_starting(self):
        node = self.node()
        calls = []
        node.preview.publish.side_effect = lambda _: calls.append('preview')
        node.send_next.side_effect = lambda: calls.append('move')
        VoiceNavigator.plan_result(node, self.result(), 1)
        self.assertEqual(calls, ['preview', 'move'])
        self.assertFalse(node.planning)
        node.fail.assert_not_called()

    def test_failed_or_empty_plan_does_not_move(self):
        for result in (self.result(GoalStatus.STATUS_ABORTED), self.result(poses=[])):
            node = self.node()
            VoiceNavigator.plan_result(node, result, 1)
            node.fail.assert_called_once()
            node.send_next.assert_not_called()
            node.preview.publish.assert_not_called()

    def test_cancel_invalidates_late_result(self):
        node = self.node()
        handle = S(cancel_goal_async=Mock())
        node.plan_handle = handle
        VoiceNavigator.stop_planning(node)
        self.assertFalse(node.planning)
        handle.cancel_goal_async.assert_called_once()
        VoiceNavigator.plan_result(node, self.result(), 1)
        node.send_next.assert_not_called()
        node.preview.publish.assert_not_called()

    def test_late_acceptance_is_canceled(self):
        node = self.node()
        node.plan_generation = 2
        handle = S(accepted=True, cancel_goal_async=Mock())
        VoiceNavigator.plan_response(node, future(handle), 1)
        handle.cancel_goal_async.assert_called_once()
        self.assertIsNone(node.plan_handle)

    def test_planning_timeout_fails_without_motion(self):
        node = self.node()
        node.plan_deadline = time.monotonic()-1
        VoiceNavigator.check_plan(node)
        node.fail.assert_called_once()
        node.send_next.assert_not_called()

    def test_unknown_middle_region_is_rejected_before_planning(self):
        regions = json.loads((Path(__file__).resolve().parents[1]/'config/regions.json').read_text())['regions']
        node = self.node()
        node.regions = {r['id']: r for r in regions}
        node.plan_route = Mock()
        VoiceNavigator.command(node, String(data='Đi từ phòng A qua phòng D rồi đến phòng B.'))
        self.assertEqual(node.status.call_args.args[0], 'INVALID')
        node.plan_route.assert_not_called()
        node.send_next.assert_not_called()


if __name__ == '__main__':
    unittest.main()
