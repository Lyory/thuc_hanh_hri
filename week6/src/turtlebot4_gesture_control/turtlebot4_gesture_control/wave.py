"""Wave = confident open palm moving sideways with at least two reversals."""
from collections import deque


class WaveDetector:
    def __init__(self, window=1.8, excursion=0.10):
        self.window, self.excursion = window, excursion
        self.points = deque()
        self.latched = False

    def update(self, now, x, y, enabled):
        if not enabled or x is None:
            self.points.clear()
            self.latched = False
            return False
        if self.points and now - self.points[-1][0] > 0.25:
            self.points.clear()
            self.latched = False
        self.points.append((now, x, y))
        while self.points and now - self.points[0][0] > self.window:
            self.points.popleft()
        if self.latched:
            return True
        if len(self.points) < 6 or now - self.points[0][0] < 0.5:
            return False
        ys = [point[2] for point in self.points]
        if max(ys) - min(ys) > 0.20:
            return False
        anchor = self.points[0][1]
        direction, reversals = 0, 0
        for _, px, _ in self.points:
            dx = px - anchor
            if direction == 0:
                if abs(dx) >= self.excursion:
                    direction = 1 if dx > 0 else -1
                    anchor = px
            elif (px - anchor) * direction >= 0:
                anchor = px
            elif abs(px - anchor) >= self.excursion:
                direction *= -1
                reversals += 1
                anchor = px
        self.latched = reversals >= 2
        return self.latched
