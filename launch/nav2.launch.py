"""Thành phần dùng chung: map_server, AMCL và các Nav2 server tuần 5."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def setup(context):
    root = Path(__file__).resolve().parents[1]
    navigation = Path(get_package_share_directory('turtlebot4_navigation'))
    servers = [('nav2_controller', 'controller_server'), ('nav2_smoother', 'smoother_server'),
               ('nav2_planner', 'planner_server'), ('nav2_behaviors', 'behavior_server'),
               ('nav2_bt_navigator', 'bt_navigator'), ('nav2_waypoint_follower', 'waypoint_follower'),
               ('nav2_velocity_smoother', 'velocity_smoother')]
    nav_nodes = []
    for package, executable in servers:
        remaps = [('/tf', 'tf'), ('/tf_static', 'tf_static'),
                  ('/global_costmap/scan', '/scan'), ('/local_costmap/scan', '/scan')]
        if executable == 'controller_server':
            remaps.append(('cmd_vel', 'cmd_vel_nav'))
        if executable == 'velocity_smoother':
            remaps += [('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'cmd_vel')]
        nav_nodes.append(Node(package=package, executable=executable, name=executable,
                              parameters=[str(root / 'config/nav2.yaml'), {'use_sim_time': True}],
                              remappings=remaps, output='screen'))
    nav_nodes.append(Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
                          name='lifecycle_manager_navigation', output='screen',
                          parameters=[{'use_sim_time': True, 'autostart': True,
                                       'node_names': [s[1] for s in servers], 'bond_timeout': 30.0}]))
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(navigation / 'launch/localization.launch.py')),
            launch_arguments={'map': LaunchConfiguration('map'), 'use_sim_time': 'true',
                              'autostart': 'true'}.items()),
        *nav_nodes,
    ]


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=str(root / 'maps/map.yaml')),
        OpaqueFunction(function=setup),
    ])
