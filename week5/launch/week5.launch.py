"""Tên launch cũ: mở bước localization; chạy navigation.launch.py riêng khi đã sẵn sàng."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(root / 'launch/localization.launch.py'))),
    ])
