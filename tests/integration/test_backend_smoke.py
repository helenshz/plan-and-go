"""Backend smoke test: building file -> Gazebo world -> TurtleBot3 sees the walls.

Spec: docs/specs/0001-yaml-to-world-backend.md (acceptance criteria 1-4).

Run inside the project conda env:  pytest -m integration
Needs a normal desktop session: in a sandbox without access to the X display,
gzserver logs `[Err] Can't open display`, which fails criterion 3.
"""

import math
import os
import re
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which('ros2') is None, reason='ROS 2 env not active'),
]

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / 'tests' / 'fixtures' / 'two_rooms.building.yaml'
LAUNCH_FILE = REPO / 'launch' / 'sim.launch.py'

SPAWN_X, SPAWN_Y = 2.0, 2.5  # centre of room_a
EXPECTED_MIN_RANGE = 1.95  # 2.0 m to wall centre line - 0.05 m half wall thickness
TOLERANCE = 0.15

# Isolate from any other ROS 2 / Gazebo instance on this machine.
ROS_DOMAIN_ID = 87
GAZEBO_PORT = 11387

ANSI = re.compile(r'\x1b\[[0-9;]*m')


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    out = tmp_path_factory.mktemp('two_rooms')
    world = out / 'two_rooms.world'
    model_dir = out / 'models'
    result = subprocess.run(
        ['ros2', 'run', 'rmf_building_map_tools', 'building_map_generator', 'gazebo',
         str(FIXTURE), str(world), str(model_dir)],
        capture_output=True, text=True, timeout=120,
    )
    return result, world, model_dir


def test_generator_writes_world(generated):
    result, world, _ = generated
    assert result.returncode == 0, result.stdout + result.stderr
    assert world.is_file()


def test_world_contains_door(generated):
    _, world, _ = generated
    root = ET.parse(world).getroot()
    names = [m.get('name') for m in root.iter('model')]
    assert 'door_ab' in names


@pytest.fixture(scope='module')
def sim(generated, tmp_path_factory):
    """Launch headless Gazebo with the robot; yield (first LaserScan, log text)."""
    result, world, model_dir = generated
    assert result.returncode == 0, 'generator failed, see test_generator_writes_world'

    log_path = tmp_path_factory.mktemp('sim') / 'launch.log'
    env = dict(os.environ)
    env.pop('TURTLEBOT3_MODEL', None)  # exercise the launch file's default
    env['ROS_DOMAIN_ID'] = str(ROS_DOMAIN_ID)
    env['GAZEBO_MASTER_URI'] = f'http://localhost:{GAZEBO_PORT}'

    with open(log_path, 'w') as log:
        proc = subprocess.Popen(
            ['ros2', 'launch', str(LAUNCH_FILE),
             f'world:={world}', f'model_dir:={model_dir}',
             f'x:={SPAWN_X}', f'y:={SPAWN_Y}', 'gui:=false'],
            env=env, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,  # own process group, so we can stop gzserver too
        )
        try:
            scan = _wait_for_scan(timeout=90.0)
        finally:
            _stop(proc)

    yield scan, ANSI.sub('', log_path.read_text())


def _wait_for_scan(timeout):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data
    from sensor_msgs.msg import LaserScan

    rclpy.init(domain_id=ROS_DOMAIN_ID)
    node = rclpy.create_node('smoke_test_scan_probe')
    scans = []
    node.create_subscription(LaserScan, '/scan', scans.append, qos_profile_sensor_data)
    try:
        deadline = time.monotonic() + timeout
        # Skip the first few scans: the robot drops 1 cm onto the floor after spawning.
        while len(scans) < 5 and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.5)
        return scans[-1] if scans else None
    finally:
        node.destroy_node()
        rclpy.shutdown()


def _stop(proc):
    if proc.poll() is not None:
        return
    pgid = os.getpgid(proc.pid)
    os.killpg(pgid, signal.SIGINT)
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        os.killpg(pgid, signal.SIGKILL)
        proc.wait()


def test_gazebo_loads_without_errors(sim):
    _, log = sim
    assert 'Successfully spawned entity' in log, log
    err_lines = [line for line in log.splitlines() if '[Err]' in line]
    assert not err_lines, '\n'.join(err_lines)


def test_scan_sees_nearest_wall(sim):
    scan, log = sim
    assert scan is not None, 'no /scan message received\n' + log
    valid = [r for r in scan.ranges if math.isfinite(r) and scan.range_min <= r <= scan.range_max]
    assert valid, 'scan has no valid ranges'
    assert min(valid) == pytest.approx(EXPECTED_MIN_RANGE, abs=TOLERANCE)
