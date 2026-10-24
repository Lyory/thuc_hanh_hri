"""Webcam gesture recognition without commanding the robot."""
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package = Path(get_package_share_directory('turtlebot4_gesture_control'))
    return LaunchDescription([
        DeclareLaunchArgument('camera_index', default_value='0'),
        DeclareLaunchArgument('show_window', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('model_path', default_value=str(package / 'models/gesture_recognizer.task')),
        Node(package='turtlebot4_gesture_control', executable='gesture_recognition_node',
             output='screen', parameters=[str(package / 'config/gesture_control.yaml'), {
                 'camera_index': ParameterValue(LaunchConfiguration('camera_index'), value_type=int),
                 'show_window': ParameterValue(LaunchConfiguration('show_window'), value_type=bool),
                 'model_path': LaunchConfiguration('model_path'),
                 'use_sim_time': False,
             }]),
    ])
