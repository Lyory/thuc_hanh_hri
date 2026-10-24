"""State machine independent of ROS; all deadlines use monotonic wall time."""
from dataclasses import dataclass
from math import pi

SELECTIONS = {'Wave': 'GREETING', 'Pointing_Up': 'BACK_AND_FORTH', 'Victory': 'CIRCLE'}
VALID = set(SELECTIONS) | {'Thumb_Up', 'Open_Palm', 'Closed_Fist'}


@dataclass(frozen=True)
class Segment:
    linear: float
    angular: float
    target: float  # metres for straight motion, radians for rotation / circle


class Behavior:
    def __init__(self, stable_time=0.45, signal_timeout=0.8,
                 selection_timeout=8.0, linear_speed=0.12,
                 angular_speed=0.45, leg_distance=0.35, circle_radius=0.45):
        values = (stable_time, signal_timeout, selection_timeout, linear_speed,
                  angular_speed, leg_distance, circle_radius)
        if any(v <= 0 for v in values):
            raise ValueError('Behavior parameters must be positive')
        self.stable_time, self.signal_timeout = stable_time, signal_timeout
        self.selection_timeout = selection_timeout
        self.linear_speed, self.angular_speed = linear_speed, angular_speed
        self.leg_distance, self.circle_radius = leg_distance, circle_radius
        self.state = 'IDLE'
        self.reason = 'Ready: select a gesture, then Thumb_Up'
        self.selected = None
        self.selected_at = 0.0
        self.last_signal = float('-inf')
        self.last_message = float('-inf')
        self.candidate, self.candidate_at = None, 0.0
        self.last_event = None
        self.plan = []
        self.progress = 0.0
        self.segment_started = 0.0
        self.progress_checkpoint = 0.0
        self.last_progress_at = 0.0

    def stop(self, reason, idle=False):
        self.state = 'IDLE' if idle else 'STOPPED'
        self.reason = reason
        self.selected = None
        self.plan = []
        self.progress = 0.0
        self.candidate = None

    def ingest(self, gesture, now):
        # A gap never counts toward the dwell time, even if the timer was delayed.
        if now - self.last_message > 0.25:
            self.candidate = None
        self.last_message = now
        if gesture not in VALID:
            self.candidate = None
            return
        self.last_signal = now
        if gesture in ('Open_Palm', 'Closed_Fist'):
            self.last_event = gesture
            self.stop('Open palm: emergency stop' if gesture == 'Open_Palm'
                      else 'Closed fist: cancelled', idle=gesture == 'Closed_Fist')
            return
        if gesture != self.candidate:
            self.candidate, self.candidate_at = gesture, now
        if now - self.candidate_at < self.stable_time or gesture == self.last_event:
            return
        self.last_event = gesture
        if self.state == 'RUNNING':
            return  # Cannot replace a running behavior with a noisy selection.
        if gesture in SELECTIONS:
            self.selected = SELECTIONS[gesture]
            self.selected_at = now
            self.state = 'SELECTED'
            self.reason = self.selected + ': waiting for Thumb_Up'
        elif gesture == 'Thumb_Up' and self.selected:
            if now - self.selected_at > self.selection_timeout:
                self.stop('Selection expired')
                return
            self.plan = self.make_plan(self.selected)
            self.progress, self.segment_started = 0.0, now
            self.progress_checkpoint, self.last_progress_at = 0.0, now
            self.state, self.reason = 'RUNNING', self.selected

    def make_plan(self, name):
        v, w = self.linear_speed, self.angular_speed
        if name == 'GREETING':
            return [Segment(0.0, w, 0.5), Segment(0.0, -w, 1.0), Segment(0.0, w, 0.5)]
        if name == 'BACK_AND_FORTH':
            return [s for _ in range(4) for s in (
                Segment(v, 0.0, self.leg_distance), Segment(-v, 0.0, self.leg_distance))]
        return [Segment(v, v / self.circle_radius, 2.0 * pi)]

    def tick(self, now):
        if self.state in ('RUNNING', 'SELECTED'):
            if now - self.last_signal > self.signal_timeout:
                self.stop('Control signal lost')
            elif self.state == 'SELECTED' and now - self.selected_at > self.selection_timeout:
                self.stop('Selection expired')
        if self.state != 'RUNNING':
            return 0.0, 0.0
        segment = self.plan[0]
        if self.progress >= segment.target:
            self.plan.pop(0)
            self.progress, self.segment_started = 0.0, now
            self.progress_checkpoint, self.last_progress_at = 0.0, now
            if not self.plan:
                self.stop('Behavior completed', idle=True)
            return 0.0, 0.0  # Brake for one cycle between segments.
        expected = segment.target / (abs(segment.angular) or abs(segment.linear))
        if self.progress >= self.progress_checkpoint + 0.005:
            self.progress_checkpoint, self.last_progress_at = self.progress, now
        if (now - self.last_progress_at > 6.0
                or now - self.segment_started > max(30.0, expected * 10.0)):
            self.stop('Motion timeout: robot stalled or simulation paused')
            return 0.0, 0.0
        return segment.linear, segment.angular

    def add_odometry(self, signed_distance, yaw_delta):
        if self.state == 'RUNNING' and self.plan:
            segment = self.plan[0]
            delta = (yaw_delta * (1 if segment.angular > 0 else -1)
                     if segment.angular else
                     signed_distance * (1 if segment.linear > 0 else -1))
            self.progress = max(0.0, self.progress + delta)
