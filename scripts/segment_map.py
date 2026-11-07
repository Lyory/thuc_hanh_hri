"""Seeded geodesic partition of reachable free space; obstacles stop region growth."""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
import yaml
from map_utils import GridMap

ROOT = Path(__file__).resolve().parents[1]


def segment(map_path, seed_path, output):
    grid = GridMap(map_path)
    cfg = yaml.safe_load(Path(seed_path).read_text())
    _, components = cv2.connectedComponents(
        (grid.clearance >= cfg['clearance']).astype(np.uint8), connectivity=4)
    start = grid.pixel(*cfg.get('start', [0., 0.]))
    component = int(components[start])
    if component == 0:
        raise ValueError('Vị trí khởi đầu không đủ clearance')
    safe = components == component
    candidates = np.argwhere(safe)
    regions = cfg['regions']
    if len(regions) < 3:
        raise ValueError('Cần tối thiểu ba vùng')
    if len({r['id'] for r in regions}) != len(regions):
        raise ValueError('ID vùng phải duy nhất')
    labels = np.zeros(grid.image.shape, np.int32)
    queue = deque()
    for i, region in enumerate(regions, 1):
        row, col = grid.pixel(*region['seed'])
        if not safe[row, col]:
            row, col = candidates[np.argmin(np.sum((candidates - [row, col])**2, axis=1))]
        if labels[row, col]:
            raise ValueError('Seed trùng nhau')
        labels[row, col] = i
        queue.append((int(row), int(col)))
        x, y = grid.world(int(row), int(col))
        region['goal'] = {'x': x, 'y': y, 'yaw': 0.0}
        region['pixel'] = [int(row), int(col)]
        region['clearance_m'] = float(grid.clearance[row, col])
    # Erode enough to close narrow doorways, identify room/corridor cores,
    # then regrow their labels. This avoids a room seed claiming the corridor.
    if cfg.get('partition_clearance'):
        _, cores = cv2.connectedComponents(
            (grid.clearance >= cfg['partition_clearance']).astype(np.uint8), connectivity=4)
        owners = [int(cores[tuple(r['pixel'])]) for r in regions]
        if 0 in owners or len(set(owners)) != len(owners):
            raise ValueError('partition_clearance phải tách được lõi an toàn riêng cho mỗi vùng')
        for i, core in enumerate(owners, 1):
            labels[cores == core] = i
        queue = deque((int(r), int(c)) for r,c in np.argwhere(labels > 0))
    # Four-neighbour wavefront gives obstacle-aware, deterministic ownership.
    while queue:
        r, c = queue.popleft()
        for nr, nc in ((r-1,c), (r+1,c), (r,c-1), (r,c+1)):
            if 0 <= nr < grid.h and 0 <= nc < grid.w and grid.free[nr,nc] and labels[nr,nc] == 0:
                labels[nr,nc] = labels[r,c]
                queue.append((nr,nc))
    overlay = cv2.cvtColor(grid.image, cv2.COLOR_GRAY2BGR)
    colors = [(90,200,90), (230,150,80), (100,100,230)]
    for i, region in enumerate(regions, 1):
        mask = labels == i
        color = colors[(i-1) % len(colors)]
        overlay[mask] = (.4 * overlay[mask] + .6 * np.array(color)).astype(np.uint8)
        r, c = region['pixel']
        cv2.circle(overlay, (c,r), 5, (0,0,0), -1)
        cv2.putText(overlay, region['id'], (c+7,r), cv2.FONT_HERSHEY_SIMPLEX, .65, (0,0,0), 2)
        region['area_m2'] = float(mask.sum() * grid.res**2)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output / 'segmented_map.png'), overlay)
    np.save(output / 'region_labels.npy', labels)
    doc = {'frame_id': 'map', 'map_yaml': str(Path(map_path).resolve()),
           'image_sha256': hashlib.sha256(grid.image.tobytes()).hexdigest(),
           'map_metadata': grid.meta, 'clearance': cfg['clearance'], 'regions': regions}
    (output / 'regions.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(doc, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--map', default=str(ROOT/'maps/map.yaml'))
    p.add_argument('--seeds', default=str(ROOT/'config/region_seeds.yaml'))
    p.add_argument('--output', default=str(ROOT/'config'))
    a = p.parse_args()
    segment(a.map, a.seeds, a.output)
