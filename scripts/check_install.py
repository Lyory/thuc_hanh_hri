"""Check installed libraries, ROS packages and launch files on Ubuntu 22.04 / ROS 2 Humble."""
import importlib
from pathlib import Path
import subprocess
import yaml
from ament_index_python.packages import get_package_share_directory

ROOT = Path(__file__).resolve().parents[1]
for name in ('rclpy', 'cv2', 'yaml', 'numpy', 'faster_whisper', 'sounddevice', 'PyQt5.QtWidgets'):
    importlib.import_module(name)
for name in ('turtlebot4_ignition_bringup', 'turtlebot4_ignition_gui_plugins',
             'turtlebot4_description', 'turtlebot4_navigation', 'irobot_create_ignition_bringup',
             'irobot_create_common_bringup', 'irobot_create_nodes', 'ign_ros2_control',
             'ros_gz_bridge', 'ros_ign_gazebo', 'robot_state_publisher', 'joint_state_publisher',
             'tf2_ros', 'nav2_bringup', 'nav2_simple_commander', 'rviz2'):
    assert Path(get_package_share_directory(name)).is_dir(), name
for name in ('maps/map.yaml', 'maps/map.pgm', 'worlds/rooms.sdf', 'config/region_seeds.yaml',
             'config/regions.json', 'config/nav2.yaml', 'config/navigation.rviz'):
    assert (ROOT/name).is_file(), name
# Launch --show-args does not load RViz's display configuration. Parse it here
# so a malformed file cannot silently leave RViz with an empty window.
rviz = yaml.safe_load((ROOT/'config/navigation.rviz').read_text())
manager = rviz['Visualization Manager']
assert manager['Global Options']['Fixed Frame'] == 'map'
assert isinstance(manager['Displays'], list) and manager['Displays']
semantic = next(d for d in manager['Displays'] if d.get('Name') == 'Semantic Regions')
assert semantic['Topic']['Value'] == '/semantic_regions'
preview = next(d for d in manager['Displays'] if d.get('Name') == 'Route Preview')
assert preview['Topic']['Value'] == '/voice_navigation/preview_path'
subprocess.run(['ign', 'gazebo', '--versions'], check=True)
subprocess.run(['ros2', 'launch', str(ROOT/'launch/week7.launch.py'), '--show-args'],
               check=True, stdout=subprocess.DEVNULL)
print('PASS: Python imports, ROS packages, map/world/config, RViz YAML and launch arguments')
