"""Gazebo Fortress + TurtleBot 4, with dock outside the gesture demo area."""
from pathlib import Path
import os
import xml.etree.ElementTree as ET

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.actions import OpaqueFunction, SetEnvironmentVariable, Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup_simulation(context):
    def share(package):
        return Path(get_package_share_directory(package))

    def include(package, filename, arguments):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(share(package) / 'launch' / filename)),
            launch_arguments=arguments.items())

    world = Path(LaunchConfiguration('world').perform(context)).expanduser().resolve()
    if not world.is_file():
        raise FileNotFoundError(f'World missing: {world}')
    world_element = ET.parse(world).getroot().find('world')
    if world_element is None:
        raise ValueError('SDF must contain a world element')
    world_name = world_element.attrib['name']
    model = LaunchConfiguration('model').perform(context)
    bringup = 'turtlebot4_ignition_bringup'
    common = 'irobot_create_common_bringup'
    create_sim = 'irobot_create_ignition_bringup'
    resources = [share(bringup) / 'worlds', share(create_sim) / 'worlds',
                 share('turtlebot4_description').parent, share('irobot_create_description').parent]
    plugins = [share(package) / 'lib' for package in
               ('turtlebot4_ignition_gui_plugins', 'irobot_create_ignition_plugins')]
    command = ['ign', 'gazebo', str(world), '-r', '-v', '3',
               '--render-engine-server', 'ogre2']
    if LaunchConfiguration('headless').perform(context) == 'true':
        command.extend(['-s', '--headless-rendering'])
    common_args = {'namespace': '', 'use_sim_time': 'true', 'gazebo': 'ignition'}
    return [
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', ':'.join(map(str, resources))),
        SetEnvironmentVariable('IGN_GUI_PLUGIN_PATH', ':'.join(map(str, plugins))),
        SetEnvironmentVariable('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', ':'.join(filter(None, [
            str(Path(get_package_prefix('ign_ros2_control')) / 'lib'),
            os.environ.get('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', '')]))),
        ExecuteProcess(cmd=command, output='screen',
                       on_exit=[Shutdown(reason='Gazebo exited')]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='clock_bridge',
             arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'], output='screen'),
        include('turtlebot4_description', 'robot_description.launch.py',
                {'model': model, 'use_sim_time': 'true', 'namespace': ''}),
        include(common, 'dock_description.launch.py', {'gazebo': 'ignition', 'namespace': ''}),
        Node(package='ros_ign_gazebo', executable='create', name='spawn_robot',
             arguments=['-name', 'turtlebot4', '-topic', 'robot_description',
                        '-x', '0', '-y', '0', '-z', '0.01', '-Y', '0'], output='screen'),
        Node(package='ros_ign_gazebo', executable='create', name='spawn_dock',
             arguments=['-name', 'standard_dock', '-topic', 'standard_dock_description',
                        '-x', '-4', '-y', '-4', '-z', '0', '-Y', '0'], output='screen'),
        include(bringup, 'ros_ign_bridge.launch.py',
                {'model': model, 'robot_name': 'turtlebot4',
                 'dock_name': 'standard_dock', 'namespace': '', 'world': world_name}),
        include(bringup, 'turtlebot4_nodes.launch.py',
                {'model': model, 'param_file': str(share(bringup) / 'config/turtlebot4_node.yaml')}),
        include(common, 'create3_nodes.launch.py', common_args),
        include(create_sim, 'create3_ignition_nodes.launch.py',
                {'robot_name': 'turtlebot4', 'dock_name': 'standard_dock', 'world': world_name}),
        Node(package='tf2_ros', executable='static_transform_publisher', name='lidar_frame',
             arguments=['0', '0', '0', '0', '0', '0',
                        'rplidar_link', 'turtlebot4/rplidar_link/rplidar']),
    ]


def generate_launch_description():
    package = Path(get_package_share_directory('turtlebot4_gesture_control'))
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=str(package / 'worlds/gesture_arena.sdf')),
        DeclareLaunchArgument('model', default_value='standard', choices=['standard', 'lite']),
        DeclareLaunchArgument('headless', default_value='false', choices=['true', 'false']),
        OpaqueFunction(function=setup_simulation),
    ])
