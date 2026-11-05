"""Start Gazebo Classic with a generated world and spawn a TurtleBot3.

Spec: docs/specs/0001-yaml-to-world-backend.md

Usage:
    ros2 launch launch/sim.launch.py world:=<path.world> model_dir:=<models/> \
        x:=2.0 y:=2.5 gui:=false

- `model_dir` is the model directory written by `building_map_generator gazebo`;
  it is prepended to GAZEBO_MODEL_PATH so `model://<building>_<level>` resolves.
- TURTLEBOT3_MODEL defaults to `burger` when unset. The upstream
  turtlebot3_gazebo launch files read it at import time and fail without it,
  so this file spawns the robot itself instead of including them.
- The generated world's <gui> block references RMF GUI plugins
  (libtoggle_*.so) that are not in the conda env. gzserver ignores <gui>,
  so headless runs are unaffected; gzclient logs an error for them.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    OpaqueFunction,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _prepend_path(var, *paths):
    parts = [p for p in paths if p] + [p for p in os.environ.get(var, '').split(':') if p]
    return SetEnvironmentVariable(var, ':'.join(parts))


def _setup(context):
    model_dir = LaunchConfiguration('model_dir').perform(context)
    tb3_model = os.environ.get('TURTLEBOT3_MODEL') or 'burger'
    tb3_share = get_package_share_directory('turtlebot3_gazebo')
    gazebo_ros_launch = os.path.join(get_package_share_directory('gazebo_ros'), 'launch')
    robot_sdf = os.path.join(tb3_share, 'models', f'turtlebot3_{tb3_model}', 'model.sdf')

    return [
        SetEnvironmentVariable('TURTLEBOT3_MODEL', tb3_model),
        # Generated building models first, then TurtleBot3 models
        # (model://turtlebot3_common is referenced by the robot SDF).
        _prepend_path(
            'GAZEBO_MODEL_PATH',
            os.path.abspath(model_dir) if model_dir else '',
            os.path.join(tb3_share, 'models'),
        ),
        # Never try to download models from the online database; everything
        # we need is local, and a missing model should fail fast.
        SetEnvironmentVariable('GAZEBO_MODEL_DATABASE_URI', ''),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gazebo_ros_launch, 'gzserver.launch.py')),
            launch_arguments={
                'world': LaunchConfiguration('world'),
                'verbose': LaunchConfiguration('verbose'),
            }.items(),
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gazebo_ros_launch, 'gzclient.launch.py')),
            condition=IfCondition(LaunchConfiguration('gui')),
        ),
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
                '-entity', f'turtlebot3_{tb3_model}',
                '-file', robot_sdf,
                '-x', LaunchConfiguration('x'),
                '-y', LaunchConfiguration('y'),
                '-z', '0.01',
                '-Y', LaunchConfiguration('yaw'),
            ],
            output='screen',
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world', description='Path to the .world file'),
        DeclareLaunchArgument(
            'model_dir', default_value='',
            description='Model directory from building_map_generator (added to GAZEBO_MODEL_PATH)'),
        DeclareLaunchArgument('gui', default_value='false', description='Also start gzclient'),
        DeclareLaunchArgument('verbose', default_value='true', description='Verbose gzserver log'),
        DeclareLaunchArgument('x', default_value='0.0', description='Robot spawn x [m]'),
        DeclareLaunchArgument('y', default_value='0.0', description='Robot spawn y [m]'),
        DeclareLaunchArgument('yaw', default_value='0.0', description='Robot spawn yaw [rad]'),
        OpaqueFunction(function=_setup),
    ])
