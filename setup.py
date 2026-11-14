from glob import glob

from setuptools import setup

setup(
    name="emotion_turtlebot",
    version="0.1.0",
    packages=["emotion_turtlebot"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/emotion_turtlebot"]),
        ("share/emotion_turtlebot", ["package.xml"]),
        ("share/emotion_turtlebot/models", glob("models/*")),
        ("share/emotion_turtlebot/launch", glob("launch/*.launch.py")),
        ("share/emotion_turtlebot/worlds", glob("worlds/*.world")),
    ],
    install_requires=["setuptools"],
    maintainer="Student",
    maintainer_email="student@example.com",
    description="Control TurtleBot using webcam facial expressions",
    license="Apache-2.0",
    entry_points={"console_scripts": ["emotion_control = emotion_turtlebot.node:main"]},
)
