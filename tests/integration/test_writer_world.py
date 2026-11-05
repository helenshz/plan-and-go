"""Parse result -> Writer -> generate_world -> Gazebo: thick walls and an open door.

Spec: docs/specs/0002-parse-result-and-writer.md (acceptance criteria 8-10).
Run inside the project conda env with access to the X display:  pytest -m integration
"""

import shutil
import xml.etree.ElementTree as ET

import pytest

from sim_helpers import (REPO, err_lines, ranges_around, run_sim, valid_ranges,
                         write_and_generate)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which('ros2') is None, reason='ROS 2 env not active'),
]

PARSE_FIXTURE = REPO / 'tests' / 'fixtures' / 'two_rooms.parse.yaml'

SPAWN_X, SPAWN_Y = 2.0, 2.5  # centre of room_a
# Nearest wall: the 0.5 m thick left wall, 2.0 m to its centre line - 0.25 m.
EXPECTED_MIN_RANGE = 1.75
TOLERANCE = 0.08  # the upstream 0.1 m wall would give ~1.92 m, outside this band
# Straight ahead (+x) through the open doorway, the next wall is ~6 m away, beyond the
# scanner's 3.5 m limit; a closed leaf would read ~1.98 m.
DOORWAY_MIN_RANGE = 3.0

ROS_DOMAIN_ID = 86
GAZEBO_PORT = 11386


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    return write_and_generate(PARSE_FIXTURE, tmp_path_factory.mktemp('two_rooms_parsed'),
                              'two_rooms')


def test_generator_writes_world_with_door(generated):
    result, world, _ = generated
    assert result.returncode == 0, result.stdout + result.stderr
    names = [m.get('name') for m in ET.parse(world).getroot().iter('model')]
    assert 'door_ab' in names


@pytest.fixture(scope='module')
def sim(generated, tmp_path_factory):
    result, world, model_dir = generated
    assert result.returncode == 0, 'generator failed, see test_generator_writes_world_with_door'
    log_path = tmp_path_factory.mktemp('sim') / 'launch.log'
    return run_sim(world, model_dir, SPAWN_X, SPAWN_Y, log_path, ROS_DOMAIN_ID, GAZEBO_PORT)


def test_gazebo_loads_without_errors(sim):
    _, log = sim
    assert 'Successfully spawned entity' in log, log
    assert not err_lines(log), '\n'.join(err_lines(log))


def test_scan_sees_thick_wall(sim):
    scan, log = sim
    assert scan is not None, 'no /scan message received\n' + log
    assert min(valid_ranges(scan)) == pytest.approx(EXPECTED_MIN_RANGE, abs=TOLERANCE)


def test_scan_looks_through_open_door(sim):
    scan, log = sim
    assert scan is not None, 'no /scan message received\n' + log
    ahead = ranges_around(scan, 0.0, half_width_deg=5.0)
    assert ahead
    assert all(r > DOORWAY_MIN_RANGE for r in ahead), ahead  # inf (no return) counts
