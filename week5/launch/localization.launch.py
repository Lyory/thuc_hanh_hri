"""Bước 1: Gazebo, RViz, map, AMCL và Nav2; chờ người dùng đặt initial pose."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=str(root / 'maps/map.yaml')),
        # Spawn registers delayed controller callbacks. Keep its launch
        # configurations (namespace/use_sim_time) available after inclusion.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(root / 'launch/simulation.launch.py'))),
        TimerAction(period=15.0, actions=[
            GroupAction([
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(str(root / 'launch/nav2.launch.py')),
                    launch_arguments={'map': LaunchConfiguration('map')}.items()),
            ]),
        ]),
    ])
