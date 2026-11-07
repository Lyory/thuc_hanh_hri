"""Deterministic checks for map transforms, clearance, and command rejection."""
import json
import math
from pathlib import Path
import tempfile
import cv2
import numpy as np
import yaml
from commands import parse_command
from map_utils import GridMap

ROOT = Path(__file__).resolve().parents[1]
regions = json.loads((ROOT/'config/regions.json').read_text())['regions']
valid = {
    'Đi đến khu vực A.': ['A'],
    'Di chuyển từ khu vực A đến khu vực B.': ['A', 'B'],
    'Đi đến phòng thí nghiệm.': ['B'],
    'Đi từ phòng A qua hành lang C rồi đến phòng B': ['A', 'C', 'B'],
    'Đi đến A rồi đến B.': ['A', 'B'],
    'Đi đến B rồi quay lại C': ['B', 'C'],
    'Đi từ phòng A qua hành lang xê rồi đến phòng bê': ['A', 'C', 'B'],
    'di den hanh lang': ['C'],
    'dừng lại': [],
}
for text, expected in valid.items():
    assert parse_command(text, regions) == expected, text
invalid = ('Đi đến khu vực D', 'Đi từ A đến D', 'Đi từ D đến B',
           'Đi đến A rồi đến khu vực D', 'A', 'Đi từ A', 'Đừng đi đến A',
           'Đi từ phòng A qua phòng D rồi đến phòng B.', 'Đi từ phòng Ad qua C đến B')
for text in invalid:
    try:
        parse_command(text, regions)
    except ValueError:
        pass
    else:
        raise AssertionError(text)
grid = GridMap(ROOT/'maps/map.yaml')
# The physical dock is too low for LiDAR; the static map must prevent paths
# through it, and the undocked robot must still have a safe starting point.
assert not grid.free[grid.pixel(.202, 0.)], 'Thiếu footprint dock trong map'
assert grid.clearance[grid.pixel(-.35, 0.)] >= .35
for region in regions:
    g = region['goal']
    assert grid.clearance[grid.pixel(g['x'], g['y'])] >= .35
labels = np.load(ROOT/'config/region_labels.npy')
assert set(np.unique(labels)) == {0, 1, 2, 3}
assert not np.any(labels[~grid.free])
for i, region in enumerate(regions, 1):
    assert labels[tuple(region['pixel'])] == i
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    cv2.imwrite(str(d/'test.pgm'), np.array([[0,127,255],[255,255,0]], np.uint8))
    doc = dict(image='test.pgm', origin=[-3., 2., math.pi/3], resolution=.2,
               free_thresh=.25, occupied_thresh=.65, negate=0)
    (d/'test.yaml').write_text(yaml.safe_dump(doc))
    m = GridMap(d/'test.yaml')
    assert not m.free[0,0] and not m.free[0,1] and m.free[0,2]
    for r in range(m.h):
        for c in range(m.w):
            assert m.pixel(*m.world(r,c)) == (r,c)
    doc['negate'] = 1
    (d/'test.yaml').write_text(yaml.safe_dump(doc))
    m = GridMap(d/'test.yaml')
    assert m.free[0,0] and not m.free[0,2]
print(f'PASS: {len(valid)} valid commands, {len(invalid)} rejected commands, labels, clearance, origin yaw, negate')
