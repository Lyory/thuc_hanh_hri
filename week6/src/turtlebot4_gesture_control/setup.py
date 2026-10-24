from glob import glob
from setuptools import find_packages, setup

package = 'turtlebot4_gesture_control'
setup(
    name=package,
    version='1.0.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package]),
        ('share/' + package, ['package.xml']),
        *[('share/' + package + '/' + folder, glob(folder + '/*'))
          for folder in ('launch', 'config', 'worlds', 'models')],
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Quan',
    maintainer_email='quan@example.com',
    description='Gesture-controlled TurtleBot 4 simulation',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'gesture_recognition_node = turtlebot4_gesture_control.gesture_recognition_node:main',
        'robot_behavior_node = turtlebot4_gesture_control.robot_behavior_node:main',
        'webcam_viewer = turtlebot4_gesture_control.webcam_viewer:main',
    ]},
)
