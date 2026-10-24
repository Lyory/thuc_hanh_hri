"""Recognition and confirmed robot behaviors; optionally start Gazebo."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package = Path(get_package_share_directory('turtlebot4_gesture_control'))
    return LaunchDescription([
        DeclareLaunchArgument('start_simulation', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('headless', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('camera_index', default_value='0'),
        DeclareLaunchArgument('show_window', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('model_path', default_value=str(package / 'models/gesture_recognizer.task')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(package / 'launch/simulation.launch.py')),
            condition=IfCondition(LaunchConfiguration('start_simulation')),
            launch_arguments={'headless': LaunchConfiguration('headless')}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(package / 'launch/gesture_recognition.launch.py')),
            launch_arguments={key: LaunchConfiguration(key)
                              for key in ('camera_index', 'show_window', 'model_path')}.items()),
        Node(package='turtlebot4_gesture_control', executable='robot_behavior_node',
             output='screen', parameters=[str(package / 'config/gesture_control.yaml'),
                                          {'use_sim_time': False}]),
    ])
