"""Motion decisions without camera or ROS dependencies (metres, seconds, radians)."""

from math import isfinite, tau


# (linear.x, angular.z, maximum duration); None means continuous motion.
MOTIONS = {
    "happy": (0.10, 0.40, None),
    "sad": (0.10, -0.40, None),
    "neutral": (0.0, 0.0, None),
    "angry": (-0.08, 0.0, 1.0),
    "surprise": (0.0, 0.60, tau / 0.60),
    "fear": (0.08, 0.0, 1.0),
}


class Controller:
    def __init__(self, stable_samples=3, timeout=2.5, threshold=50.0):
        self.stable_samples = stable_samples
        self.timeout = timeout
        self.threshold = threshold
        self.active = "neutral"
        self.started = 0.0
        self.last_seen = float("-inf")
        self.candidate = None
        self.count = 0
        self.ready = False

    def invalidate(self):
        self.ready = False
        self.candidate = None
        self.count = 0

    def observe(self, emotion, confidence, captured_at, now):
        if (emotion not in MOTIONS or not isfinite(confidence)
                or confidence < self.threshold
                or not 0 <= now - captured_at <= self.timeout):
            self.invalidate()
            return
        # A gap between results must not count as consecutive observations.
        if now - self.last_seen > self.timeout:
            self.invalidate()
        self.last_seen = captured_at
        if emotion == "neutral":
            self.active = "neutral"
            self.invalidate()
            return
        self.count = self.count + 1 if emotion == self.candidate else 1
        self.candidate = emotion
        if emotion != self.active:
            # Stop while a different expression is being confirmed.
            self.ready = False
        if self.count >= self.stable_samples:
            if emotion != self.active:
                self.active = emotion
                self.started = now
            self.ready = True

    def command(self, now):
        if now - self.last_seen > self.timeout:
            self.invalidate()
        if not self.ready:
            return 0.0, 0.0
        linear, angular, duration = MOTIONS[self.active]
        if duration is not None and now - self.started >= duration:
            return 0.0, 0.0
        return linear, angular
