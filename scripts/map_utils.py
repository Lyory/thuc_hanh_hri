"""ROS trinary map semantics and pixel-centre transforms, including origin yaw."""
from pathlib import Path
import math
import cv2
import numpy as np
import yaml


class GridMap:
    def __init__(self, filename):
        filename = Path(filename)
        self.meta = yaml.safe_load(filename.read_text())
        if self.meta.get('mode', 'trinary') != 'trinary':
            raise ValueError('Chỉ hỗ trợ map trinary')
        self.image = cv2.imread(str(filename.parent / self.meta['image']), 0)
        if self.image is None:
            raise ValueError('Không đọc được ảnh map')
        self.h, self.w = self.image.shape
        self.res = float(self.meta['resolution'])
        if self.res <= 0:
            raise ValueError('resolution phải dương')
        self.ox, self.oy, self.yaw = self.meta['origin']
        self.c, self.s = math.cos(self.yaw), math.sin(self.yaw)
        occupancy = self.image.astype(float) / 255
        if not self.meta.get('negate', 0):
            occupancy = 1 - occupancy
        self.free = occupancy < float(self.meta['free_thresh'])
        # Zero border treats outside the image as unsafe too.
        padded = np.pad(self.free.astype(np.uint8), 1)
        self.clearance = cv2.distanceTransform(padded, cv2.DIST_L2, 5)[1:-1, 1:-1] * self.res

    def world(self, row, col):
        x, y = (col + .5) * self.res, (self.h - row - .5) * self.res
        return [self.ox + self.c*x - self.s*y, self.oy + self.s*x + self.c*y]

    def pixel(self, x, y):
        dx, dy = x-self.ox, y-self.oy
        col = math.floor((self.c*dx + self.s*dy) / self.res)
        row = self.h - 1 - math.floor((-self.s*dx + self.c*dy) / self.res)
        if not (0 <= row < self.h and 0 <= col < self.w):
            raise ValueError('Tọa độ nằm ngoài map')
        return row, col
