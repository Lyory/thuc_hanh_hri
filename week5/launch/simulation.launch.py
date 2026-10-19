"""Gazebo, robot và RViz dùng chung cho navigation và mapping."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction, ExecuteProcess, SetEnvironmentVariable, Shutdown
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.substitutions import EnvironmentVariable
from launch_ros.actions import Node


def setup(context):
    root = Path(__file__).resolve().parents[1]
    bringup = Path(get_package_share_directory('turtlebot4_ignition_bringup'))
    headless = LaunchConfiguration('headless').perform(context) == 'true'
    rviz_enabled = LaunchConfiguration('rviz').perform(context)
    world = Path(LaunchConfiguration('world').perform(context)).expanduser().resolve()
    if not world.is_file():
        raise FileNotFoundError(f'Không tìm thấy world: {world}')
    args = ['ign', 'gazebo', str(world), '-r', '-v', '3',
            '--render-engine-server', 'ogre2', '--render-engine-gui', 'ogre']
    args += ['-s'] if headless else ['--gui-config', str(root / 'config/gazebo_gui.config')]
    resources = [root / 'models', bringup / 'worlds',
                 Path(get_package_share_directory('irobot_create_ignition_bringup')) / 'worlds',
                 Path(get_package_share_directory('turtlebot4_description')).parent.resolve(),
                 Path(get_package_share_directory('irobot_create_description')).parent.resolve()]
    plugins = [Path(get_package_share_directory(p)) / 'lib' for p in
               ('turtlebot4_ignition_gui_plugins', 'irobot_create_ignition_plugins')]
    return [
        SetEnvironmentVariable('IGN_GAZEBO_RESOURCE_PATH', ':'.join(map(str, resources))),
        SetEnvironmentVariable('IGN_GUI_PLUGIN_PATH', ':'.join(map(str, plugins))),
        SetEnvironmentVariable('IGN_GAZEBO_SYSTEM_PLUGIN_PATH', '/opt/ros/humble/lib'),
        SetEnvironmentVariable('IGN_IP', '127.0.0.1'),
        ExecuteProcess(cmd=args, output='screen',
                       on_exit=[Shutdown(reason='Gazebo đã đóng; dừng các node mô phỏng')]),
        Node(package='ros_gz_bridge', executable='parameter_bridge', name='clock_bridge',
             arguments=['/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock'], output='screen'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(str(bringup / 'launch/turtlebot4_spawn.launch.py')),
            launch_arguments={'model': 'standard', 'rviz': 'false', 'use_sim_time': 'true',
                              'x': LaunchConfiguration('x'), 'y': LaunchConfiguration('y'),
                              'yaw': LaunchConfiguration('yaw'),
                              'world': LaunchConfiguration('world_name'), 'slam': 'false', 'nav2': 'false',
                              'localization': 'false'}.items()),
        Node(package='rviz2', executable='rviz2', name='rviz2',
             arguments=['-d', LaunchConfiguration('rviz_config')],
             parameters=[{'use_sim_time': True}], output='screen',
             additional_env={'DISPLAY': LaunchConfiguration('rviz_display'),
                             'LIBGL_ALWAYS_SOFTWARE': '1', '__GLX_VENDOR_LIBRARY_NAME': 'mesa'},
             condition=IfCondition(rviz_enabled)),
    ]


def generate_launch_description():
    root = Path(__file__).resolve().parents[1]
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=str(root / 'worlds/maze.sdf')),
        DeclareLaunchArgument('world_name', default_value='maze', description='Tên <world name=...> trong SDF'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='3.141592653589793'),
        DeclareLaunchArgument('rviz_config', default_value=str(root / 'config/navigation.rviz')),
        DeclareLaunchArgument('headless', default_value='false', choices=['true', 'false']),
        DeclareLaunchArgument('rviz', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('rviz_display', default_value=EnvironmentVariable('DISPLAY', default_value=':0')),
        OpaqueFunction(function=setup),
    ])
