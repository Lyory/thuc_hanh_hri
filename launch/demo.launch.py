"""One command opens a simple Gazebo room, TurtleBot3 and the expression camera."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess, RegisterEventHandler, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    project = Path(get_package_share_directory("emotion_turtlebot"))
    turtlebot = Path(get_package_share_directory("turtlebot3_gazebo"))
    model_path = str(turtlebot / "models")
    if os.environ.get("GAZEBO_MODEL_PATH"):
        model_path += ":" + os.environ["GAZEBO_MODEL_PATH"]
    # Keep the sensor working without painting hundreds of laser rays over the robot.
    robot_sdf = Path("/tmp/week8_turtlebot3.sdf")
    robot_sdf.write_text((turtlebot / "models/turtlebot3_burger/model.sdf").read_text()
                        .replace("<visualize>true</visualize>", "<visualize>false</visualize>"))
    server = ExecuteProcess(cmd=[
        "gzserver", "--verbose", str(project / "worlds/simple_room.world"),
        "-s", "libgazebo_ros_init.so", "-s", "libgazebo_ros_factory.so",
    ], output="screen")
    client = ExecuteProcess(cmd=["gzclient"], output="screen",
                            condition=IfCondition(LaunchConfiguration("gui")))
    camera = Node(
        package="emotion_turtlebot", executable="emotion_control", output="screen",
        parameters=[{"camera_index": ParameterValue(LaunchConfiguration("camera_index"), value_type=int)}],
        condition=IfCondition(LaunchConfiguration("camera")),
    )
    return LaunchDescription([
        DeclareLaunchArgument("gui", default_value="true"),
        DeclareLaunchArgument("camera", default_value="true"),
        DeclareLaunchArgument("camera_index", default_value="0"),
        SetEnvironmentVariable("GAZEBO_MODEL_PATH", model_path),
        SetEnvironmentVariable("GAZEBO_MODEL_DATABASE_URI", ""),
        server, client,
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[{"use_sim_time": True, "robot_description":
                          (turtlebot / "urdf/turtlebot3_burger.urdf").read_text()}],
             output="screen"),
        Node(package="gazebo_ros", executable="spawn_entity.py", output="screen",
             arguments=["-entity", "turtlebot3_burger", "-file",
                        str(robot_sdf),
                        "-x", "0", "-y", "0", "-z", "0.01", "-timeout", "60"]),
        camera,
        *[RegisterEventHandler(OnProcessExit(
            target_action=process,
            on_exit=[EmitEvent(event=Shutdown(reason="Demo window or process closed"))],
        )) for process in (server, client, camera)],
    ])
