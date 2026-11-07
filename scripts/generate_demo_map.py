"""Generate the compact occupancy map and Gazebo world from the same geometry."""
from pathlib import Path
import xml.etree.ElementTree as ET
import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
# (name, centre x/y, width/depth): every collision also appears in the map.
WALLS = [
    ('south', 0, -2., 9., .16), ('north', 0, 3.5, 9., .16),
    ('west', -4.5, .75, .16, 5.5), ('east', 4.5, .75, .16, 5.5),
    ('divider', 0, 2.15, .16, 2.7),
    ('room_a_left', -3.65, .8, 1.7, .16),
    ('room_a_right', -.65, .8, 1.3, .16),
    ('room_b_left', .65, .8, 1.3, .16),
    ('room_b_right', 3.65, .8, 1.7, .16),
    ('cabinet_a', -3.65, 2.8, .65, .55),
    ('cabinet_b', 3.65, 2.8, .65, .55),
]
# The spawn launch places standard_dock at x=.157, yaw=pi. Its Humble
# collision box is offset -.045 locally and measures .04 x .13 x .10 m.
# It is below the LiDAR at ~.19 m, so the known footprint must be mapped.
DOCK = (.202, 0., .04, .13)


def generate():
    res, ox, oy, width, height = .05, -5., -2.5, 200, 140
    xs = ox + (np.arange(width) + .5)*res
    ys = oy + (height - np.arange(height) - .5)*res
    xx, yy = np.meshgrid(xs, ys)
    image = np.full((height, width), 205, np.uint8)
    image[(abs(xx) < 4.5) & (yy > -2) & (yy < 3.5)] = 254
    for _, x, y, w, h in WALLS:
        image[(abs(xx-x) <= w/2) & (abs(yy-y) <= h/2)] = 0
    x,y,w,h = DOCK
    # Mark every intersecting pixel: a .04 m box is narrower than one pixel.
    image[(abs(xx-x) < w/2+res/2) & (abs(yy-y) < h/2+res/2)] = 0
    cv2.imwrite(str(ROOT/'maps/map.pgm'), image)
    (ROOT/'maps/map.yaml').write_text(yaml.safe_dump(dict(image='map.pgm', mode='trinary',
        resolution=res, origin=[ox, oy, 0.], negate=0, occupied_thresh=.65, free_thresh=.196)))
    sdf = ET.Element('sdf', version='1.8')
    world = ET.SubElement(sdf, 'world', name='rooms')
    physics = ET.SubElement(world, 'physics', name='default', type='ignored')
    ET.SubElement(physics, 'max_step_size').text = '.005'
    ET.SubElement(physics, 'real_time_factor').text = '1'
    ET.SubElement(physics, 'real_time_update_rate').text = '200'
    for name, filename in [('Physics','physics'), ('UserCommands','user-commands'),
                           ('SceneBroadcaster','scene-broadcaster'), ('Contact','contact')]:
        ET.SubElement(world, 'plugin', name=f'ignition::gazebo::systems::{name}',
                      filename=f'ignition-gazebo-{filename}-system')
    ET.SubElement(world, 'gravity').text = '0 0 -9.8'
    scene = ET.SubElement(world, 'scene')
    ET.SubElement(scene, 'ambient').text = '.7 .7 .7 1'
    ET.SubElement(scene, 'background').text = '.9 .93 .96 1'
    ET.SubElement(scene, 'shadows').text = 'false'
    light = ET.SubElement(world, 'light', name='sun', type='directional')
    ET.SubElement(light, 'pose').text = '0 0 10 0 0 0'
    ET.SubElement(light, 'diffuse').text = '.8 .8 .8 1'
    ET.SubElement(light, 'direction').text = '-.5 .1 -.9'

    def box(name, x, y, w, d, z, colour, collision=True):
        model = ET.SubElement(world, 'model', name=name)
        ET.SubElement(model, 'static').text = 'true'
        ET.SubElement(model, 'pose').text = f'{x} {y} {z/2} 0 0 0'
        link = ET.SubElement(model, 'link', name='body')
        for kind in (('collision', 'visual') if collision else ('visual',)):
            element = ET.SubElement(link, kind, name=kind)
            geometry = ET.SubElement(element, 'geometry')
            ET.SubElement(ET.SubElement(geometry, 'box'), 'size').text = f'{w} {d} {z}'
            if kind == 'visual':
                material = ET.SubElement(element, 'material')
                for prop in ('ambient', 'diffuse'):
                    ET.SubElement(material, prop).text = colour
    # Top surface at zero; coloured tiles are visual only.
    floor = ET.SubElement(world, 'model', name='floor')
    ET.SubElement(floor, 'static').text = 'true'
    ET.SubElement(floor, 'pose').text = '0 .75 -.05 0 0 0'
    link = ET.SubElement(floor, 'link', name='body')
    for kind in ('collision', 'visual'):
        element = ET.SubElement(link, kind, name=kind)
        ET.SubElement(ET.SubElement(ET.SubElement(element, 'geometry'), 'box'), 'size').text = '10 7 .1'
    box('floor_a', -2.25, 2.15, 4.3, 2.5, .002, '.65 .88 .75 1', False)
    box('floor_b', 2.25, 2.15, 4.3, 2.5, .002, '.66 .8 .98 1', False)
    box('floor_c', 0, -.6, 8.8, 2.6, .002, '.98 .87 .59 1', False)
    for name,x,y,w,d in WALLS:
        box(name,x,y,w,d,1.1,'.22 .28 .36 1')
    ET.indent(sdf)
    ET.ElementTree(sdf).write(ROOT/'worlds/rooms.sdf', encoding='utf-8', xml_declaration=True)
    print('Generated 10 × 7 m map (200 × 140 pixels) and matching rooms.sdf')


if __name__ == '__main__':
    generate()
