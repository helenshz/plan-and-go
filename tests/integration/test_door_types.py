"""Hinged and sliding doors end up at the right place, size, type and open pose.

Spec: docs/specs/0002-parse-result-and-writer.md (acceptance criteria 12-13).
Fixture: tests/fixtures/door_types.parse.yaml (layout drawn in its header).
Run inside the project conda env with access to the X display:  pytest -m integration
"""

import math
import shutil
import xml.etree.ElementTree as ET

import pytest

from plan_and_go.door_geometry import open_leaves
from sim_helpers import (REPO, err_lines, ranges_around, run_sim, write_and_generate)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(shutil.which('ros2') is None, reason='ROS 2 env not active'),
]

PARSE_FIXTURE = REPO / 'tests' / 'fixtures' / 'door_types.parse.yaml'

# Expected doors in metres, worked out by hand from the fixture's pixels (100 px/m).
DOORS = {
    'door_hinged': {'p1': (1.55, 4.0), 'p2': (2.45, 4.0), 'type': 'hinged',
                    'joint': 'revolute', 'wall_axis': (1.0, 0.0)},
    'door_sliding': {'p1': (4.0, 1.4), 'p2': (4.0, 2.6), 'type': 'sliding',
                     'joint': 'prismatic', 'wall_axis': (0.0, 1.0)},
}
POS_TOL = 0.01  # [m]

# Robot in room_a; the sliding door is straight ahead (0 deg), the hinged door to the left (90 deg).
SPAWN_X, SPAWN_Y = 2.0, 2.0
DOOR_DIRECTIONS = {'door_sliding': 0.0, 'door_hinged': 90.0}
DOORWAY_MIN_RANGE = 3.0

ROS_DOMAIN_ID = 84
GAZEBO_PORT = 11384


@pytest.fixture(scope='module')
def generated(tmp_path_factory):
    return write_and_generate(PARSE_FIXTURE, tmp_path_factory.mktemp('door_types'), 'door_types')


@pytest.fixture(scope='module')
def door_models(generated):
    result, world, _ = generated
    assert result.returncode == 0, result.stdout + result.stderr
    models = {m.get('name'): m for m in ET.parse(world).getroot().iter('model')}
    return {name: models.get(name) for name in DOORS}


def _pose(text):
    x, y, _z, _r, _p, yaw = (float(v) for v in text.split())
    return x, y, yaw


def _model(door_models, name):
    model = door_models[name]
    assert model is not None, f'{name} missing from the world'
    return model


@pytest.mark.parametrize('name', DOORS)
def test_door_is_static_at_middle_of_opening(door_models, name):
    model = _model(door_models, name)
    exp = DOORS[name]
    assert model.findtext('static') == 'true'
    x, y, _ = _pose(model.findtext('pose'))
    mid = ((exp['p1'][0] + exp['p2'][0]) / 2, (exp['p1'][1] + exp['p2'][1]) / 2)
    assert (x, y) == pytest.approx(mid, abs=POS_TOL)


@pytest.mark.parametrize('name', DOORS)
def test_door_frame_lies_along_its_wall(door_models, name):
    _, _, yaw = _pose(_model(door_models, name).findtext('pose'))
    wx, wy = DOORS[name]['wall_axis']
    # door x axis parallel to the wall (either sense): cross product ~ 0
    assert abs(math.cos(yaw) * wy - math.sin(yaw) * wx) == pytest.approx(0.0, abs=1e-3)


@pytest.mark.parametrize('name', DOORS)
def test_leaf_width_and_joint_type(door_models, name):
    model = _model(door_models, name)
    exp = DOORS[name]
    width = math.dist(exp['p1'], exp['p2'])
    size = [float(v) for v in model.find('link/visual/geometry/box/size').text.split()]
    assert size[0] == pytest.approx(width - 0.01, abs=1e-3)
    [joint] = model.findall('joint')
    assert joint.get('type') == exp['joint']


@pytest.mark.parametrize('name', DOORS)
def test_leaf_is_in_open_pose(door_models, name):
    model = _model(door_models, name)
    exp = DOORS[name]
    mx, my, myaw = _pose(model.findtext('pose'))
    lx, ly, lyaw = _pose(model.find('link').findtext('pose'))
    leaf_x = mx + math.cos(myaw) * lx - math.sin(myaw) * ly
    leaf_y = my + math.sin(myaw) * lx + math.cos(myaw) * ly
    leaf_yaw = myaw + lyaw

    [expected] = open_leaves(exp['p1'], exp['p2'], exp['type'])
    assert (leaf_x, leaf_y) == pytest.approx((expected.x, expected.y), abs=POS_TOL)

    # Independent of door_geometry: how the leaf sits relative to the wall.
    wx, wy = exp['wall_axis']
    along = abs(math.cos(leaf_yaw) * wx + math.sin(leaf_yaw) * wy)
    width = math.dist(exp['p1'], exp['p2'])
    mid = ((exp['p1'][0] + exp['p2'][0]) / 2, (exp['p1'][1] + exp['p2'][1]) / 2)
    if exp['type'] == 'hinged':
        assert along == pytest.approx(0.0, abs=1e-2)  # perpendicular to the wall
    else:
        assert along == pytest.approx(1.0, abs=1e-3)  # parallel to the wall
        assert math.dist((leaf_x, leaf_y), mid) == pytest.approx(width, abs=POS_TOL)


@pytest.fixture(scope='module')
def sim(generated, tmp_path_factory):
    result, world, model_dir = generated
    assert result.returncode == 0, result.stdout + result.stderr
    log_path = tmp_path_factory.mktemp('sim') / 'launch.log'
    return run_sim(world, model_dir, SPAWN_X, SPAWN_Y, log_path, ROS_DOMAIN_ID, GAZEBO_PORT)


def test_gazebo_loads_without_errors(sim):
    _, log = sim
    assert 'Successfully spawned entity' in log, log
    assert not err_lines(log), '\n'.join(err_lines(log))


@pytest.mark.parametrize('name', DOOR_DIRECTIONS)
def test_scan_looks_through_doorway(sim, name):
    scan, log = sim
    assert scan is not None, 'no /scan message received\n' + log
    ahead = ranges_around(scan, DOOR_DIRECTIONS[name], half_width_deg=5.0)
    assert ahead
    assert all(r > DOORWAY_MIN_RANGE for r in ahead), (name, ahead)  # inf (no return) counts
