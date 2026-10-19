"""Bước 2: chạy goal tự động và camera YOLO, giữ pose đã đặt ở bước 1."""
from pathlib import Path
import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import EnvironmentVariable, LaunchConfiguration


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    gui_env = {'DISPLAY': LaunchConfiguration('yolo_display'),
               'LIBGL_ALWAYS_SOFTWARE': '1', '__GLX_VENDOR_LIBRARY_NAME': 'mesa'}
    if os.environ.get('XAUTHORITY'):
        gui_env['XAUTHORITY'] = os.environ['XAUTHORITY']
    elif Path('/tmp/tb4.Xauthority').is_file():
        gui_env['XAUTHORITY'] = '/tmp/tb4.Xauthority'
    return LaunchDescription([
        DeclareLaunchArgument('goals', default_value=str(root / 'config/goals.yaml')),
        DeclareLaunchArgument('yolo_display', default_value=EnvironmentVariable('DISPLAY', default_value=':0')),
        ExecuteProcess(
            cmd=[str(root / '.venv/bin/python'), str(root / 'scripts/yolo_detector.py'), '--show'],
            additional_env=gui_env,
            output='screen'),
        ExecuteProcess(
            cmd=['python3', str(root / 'scripts/navigate_goals.py'),
                 '--goals', LaunchConfiguration('goals')],
            output='screen'),
    ])
