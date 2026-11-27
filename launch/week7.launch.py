from pathlib import Path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    return LaunchDescription([
        DeclareLaunchArgument('headless', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false'),
        DeclareLaunchArgument('panel', default_value='true'),
        DeclareLaunchArgument('auto_initialize', default_value='true'),
        DeclareLaunchArgument('map', default_value=str(root/'maps/map.yaml')),
        DeclareLaunchArgument('regions', default_value=str(root/'config/regions.json')),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(root/'launch/localization.launch.py'))),
        ExecuteProcess(cmd=['python3', str(root/'scripts/initialize.py')],
                       condition=IfCondition(LaunchConfiguration('auto_initialize')), output='screen'),
        ExecuteProcess(cmd=['python3', str(root/'scripts/voice_panel.py')],
                       condition=IfCondition(LaunchConfiguration('panel')), output='screen'),
        ExecuteProcess(cmd=['python3', str(root/'scripts/voice_navigation.py'),
                            '--map', LaunchConfiguration('map'), '--regions', LaunchConfiguration('regions')], output='screen'),
    ])
