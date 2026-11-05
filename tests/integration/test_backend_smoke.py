"""Backend smoke test: building file -> Gazebo world -> TurtleBot3 sees the walls.

Spec: docs/specs/0001-yaml-to-world-backend.md (acceptance criteria 1-4).

Run inside the project conda env:  pytest -m integration
Needs a normal desktop session: in a sandbox without access to the X display,
gzserver logs `[Err] Can't open display`, which fails criterion 3.
"""

import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest

from sim_helpers import REPO, err_lines, run_sim, valid_ranges

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which('ros2') is None, reason='ROS 2 env not active'),
]

FIXTURE = REPO / 'tests' / 'fixtures' / 'two_rooms.building.yaml'

SPAWN_X, SPAWN_Y = 2.0, 2.5  # centre of room_a
EXPECTED_MIN_RANGE = 1.95  # 2.0 m to wall centre line - 0.05 m half wall thickness
TOLERANCE = 0.15

# Isolate from any other ROS 2 / Gazebo instance on this machine.
ROS_DOMAIN_ID = 87
GAZEBO_PORT = 11387


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
    """Headless Gazebo with the robot in room_a: (last LaserScan, log text)."""
    result, world, model_dir = generated
    assert result.returncode == 0, 'generator failed, see test_generator_writes_world'
    log_path = tmp_path_factory.mktemp('sim') / 'launch.log'
    return run_sim(world, model_dir, SPAWN_X, SPAWN_Y, log_path, ROS_DOMAIN_ID, GAZEBO_PORT)


def test_gazebo_loads_without_errors(sim):
    _, log = sim
    assert 'Successfully spawned entity' in log, log
    assert not err_lines(log), '\n'.join(err_lines(log))


def test_scan_sees_nearest_wall(sim):
    scan, log = sim
    assert scan is not None, 'no /scan message received\n' + log
    valid = valid_ranges(scan)
    assert valid, 'scan has no valid ranges'
    assert min(valid) == pytest.approx(EXPECTED_MIN_RANGE, abs=TOLERANCE)
