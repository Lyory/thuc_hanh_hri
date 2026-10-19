"""Simulation + RViz + SLAM để quét bản đồ mới bằng teleop."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    navigation = Path(get_package_share_directory('turtlebot4_navigation'))
    return LaunchDescription([
        DeclareLaunchArgument('slam_params', default_value=str(root / 'config/slam.yaml')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(root / 'launch/simulation.launch.py')),
            launch_arguments={'rviz_config': str(root / 'config/mapping.rviz')}.items()),
        TimerAction(period=15.0, actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(str(navigation / 'launch/slam.launch.py')),
                launch_arguments={'use_sim_time': 'true', 'sync': 'false',
                                  'params': LaunchConfiguration('slam_params')}.items()),
        ]),
    ])
